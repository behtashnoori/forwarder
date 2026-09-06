"""Operator-only transaction bridge across the immutable-event metadata backfill."""
from alembic import command
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

BACKFILL = "20260812_operational_execution"
PREDECESSOR = "security_credential_remediation"
FUNCTION = "public.phase1a_reject_milestone_event_mutation_v1"
STRICT = f"""CREATE OR REPLACE FUNCTION {FUNCTION}() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'milestone_event is append-only' USING ERRCODE='55000'; END; $$"""
BRIDGE = f"""CREATE OR REPLACE FUNCTION {FUNCTION}() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='UPDATE'
    AND (to_jsonb(OLD)->>'public_id') IS NULL
    AND (to_jsonb(OLD)->>'organization_id') IS NULL
    AND (to_jsonb(NEW)-'public_id'-'organization_id')=(to_jsonb(OLD)-'public_id'-'organization_id')
    AND (to_jsonb(NEW)->>'public_id') ~ '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$'
    AND (to_jsonb(NEW)->>'organization_id')::bigint=(
      SELECT organization_id FROM operational_milestone WHERE id=OLD.milestone_id)
 THEN RETURN NEW; END IF;
 RAISE EXCEPTION 'milestone_event is append-only' USING ERRCODE='55000';
END; $$"""


def _contains(script, revisions, target):
    return any(row.revision == target for row in script.walk_revisions(base="base", head=revisions))


def upgrade_with_bridge(cfg, revision, engine):
    """Use the same connection for bridge DDL, historical upgrade, and restoration.

    No privilege changes. The exclusive lock and transaction prevent other sessions
    from using temporary permissions. A failed upgrade rolls back the function too.
    """
    if engine.dialect.name != "postgresql":
        command.upgrade(cfg, revision)
        return
    script = ScriptDirectory.from_config(cfg)
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_heads()
    if not _contains(script, revision, BACKFILL) or (
        current and _contains(script, current, BACKFILL)
    ):
        command.upgrade(cfg, revision)
        return
    # Stop immediately before the known backfill, without changing historical files.
    command.upgrade(cfg, PREDECESSOR)
    with engine.begin() as connection:
        connection.execute(text("LOCK TABLE milestone_event IN ACCESS EXCLUSIVE MODE"))
        trigger = connection.execute(text("""SELECT t.tgenabled, p.oid::regprocedure::text
            FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
            WHERE t.tgrelid='milestone_event'::regclass AND t.tgname='trg_milestone_event_append_only'""")).one()
        if trigger[0] not in ("O", "A") or "phase1a_reject_milestone_event_mutation_v1" not in trigger[1]:
            raise RuntimeError("Unexpected append-only trigger; operator inspection required")
        original = connection.execute(text(f"SELECT pg_get_functiondef('{FUNCTION}()'::regprocedure)")).scalar_one()
        if "55000" not in original or "RETURN NEW" in original.upper():
            raise RuntimeError("Unexpected append-only function; refusing bridge")
        populated = connection.execute(text("SELECT EXISTS(SELECT 1 FROM milestone_event)")).scalar_one()
        if populated:
            connection.execute(text(BRIDGE))
        cfg.attributes["connection"] = connection
        try:
            command.upgrade(cfg, BACKFILL)
            connection.execute(text(STRICT))
            restored = connection.execute(text(f"SELECT pg_get_functiondef('{FUNCTION}()'::regprocedure)")).scalar_one()
            if "55000" not in restored or "RETURN NEW" in restored.upper():
                raise RuntimeError("Append-only restoration could not be verified")
        finally:
            cfg.attributes.pop("connection", None)
    command.upgrade(cfg, revision)
