"""Run against an operator-prepared disposable PostgreSQL qualification database.

Use STEP3A_POSTGRES_URL; never production. Scenarios intentionally require their
own prepared database instead of deleting or stamping an existing database.
"""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from backend import milestone_upgrade_bridge as bridge
from backend.migration_runtime import alembic_config, database_engine, prepare_version_table_for_upgrade


def rejected(connection, sql, parameters=None):
    try:
        with connection.begin_nested():
            connection.execute(text(sql), parameters or {})
    except DBAPIError as error:
        assert getattr(error.orig, "sqlstate", getattr(error.orig, "pgcode", None)) == "55000"
    else:
        raise AssertionError("Historical mutation was accepted")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=["empty", "populated", "already", "rollback"])
    parser.add_argument("--confirm-disposable", action="store_true", required=True)
    args = parser.parse_args()
    engine = database_engine(os.environ["STEP3A_POSTGRES_URL"])
    assert engine.dialect.name == "postgresql"
    cfg = alembic_config(os.environ["STEP3A_POSTGRES_URL"])
    before = []
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_heads()
        if args.scenario == "empty":
            assert not inspect(connection).get_table_names(), "Empty scenario requires an empty database"
        else:
            if args.scenario in {"populated", "rollback"}:
                assert current == (bridge.PREDECESSOR,), "Prepare the historical predecessor with real fixture events"
            else:
                assert current == ("20260912_execution_authority",)
            before = connection.execute(text("""SELECT id, to_jsonb(e)-'public_id'-'organization_id'-'source_channel'
                -'event_location_id'-'note'-'verification_state'-'verified_by_user_id'-'verified_at'-'related_event_id'
                FROM milestone_event e ORDER BY id""")).all()
            assert before, "Populated qualification requires occurrence fixture rows"
    prepare_version_table_for_upgrade(os.environ["STEP3A_POSTGRES_URL"], cfg)
    if args.scenario == "rollback":
        original_upgrade = bridge.command.upgrade
        def injected(config, revision):
            if revision == bridge.BACKFILL:
                # Fail after historical DDL/backfill, proving they roll back together.
                original_upgrade(config, revision)
                raise RuntimeError("qualification injected failure")
            return original_upgrade(config, revision)
        bridge.command.upgrade = injected
        try:
            try:
                bridge.upgrade_with_bridge(cfg, "head", engine)
            except RuntimeError as error:
                assert str(error) == "qualification injected failure"
            else:
                raise AssertionError("Failure injection did not execute")
        finally:
            bridge.command.upgrade = original_upgrade
        with engine.connect() as connection:
            assert MigrationContext.configure(connection).get_current_heads() == current
            rejected(connection, "UPDATE milestone_event SET reason='rejected' WHERE id=:id", {"id": before[0][0]})
            rejected(connection, "DELETE FROM milestone_event WHERE id=:id", {"id": before[0][0]})
    else:
        bridge.upgrade_with_bridge(cfg, "head", engine)
        bridge.upgrade_with_bridge(cfg, "head", engine)  # Already-upgraded replay.
        with engine.connect() as connection:
            assert MigrationContext.configure(connection).get_current_heads() == ("20260912_execution_authority",)
            if before:
                after = connection.execute(text("""SELECT id, to_jsonb(e)-'public_id'-'organization_id'-'source_channel'
                    -'event_location_id'-'note'-'verification_state'-'verified_by_user_id'-'verified_at'-'related_event_id'
                    FROM milestone_event e ORDER BY id""")).all()
                assert before == after
                rejected(connection, "UPDATE milestone_event SET reason='rejected' WHERE id=:id", {"id": before[0][0]})
                rejected(connection, "DELETE FROM milestone_event WHERE id=:id", {"id": before[0][0]})
                # These fixture decisions roll back at connection close.
                root = connection.execute(text("""SELECT e.id FROM milestone_event e
                    WHERE e.event_type IN ('reported','corrected','CORRECTED') AND NOT EXISTS (
                    SELECT 1 FROM milestone_event c WHERE c.supersedes_event_id=e.id
                    AND c.event_type IN ('corrected','CORRECTED')) ORDER BY e.id LIMIT 1""")).scalar_one()
                connection.execute(text("""INSERT INTO milestone_event
                    (public_id,organization_id,milestone_id,event_type,occurred_at,recorded_at,actor_user_id,
                     related_event_id,idempotency_key,request_hash)
                    SELECT gen_random_uuid()::text,organization_id,milestone_id,'VERIFIED',occurred_at,now(),
                     actor_user_id,id,'qualification-verify-'||gen_random_uuid()::text,'qualification'
                    FROM milestone_event WHERE id=:id"""), {"id": root})
                connection.execute(text("""INSERT INTO milestone_event
                    (public_id,organization_id,milestone_id,event_type,occurred_at,recorded_at,actor_user_id,
                     supersedes_event_id,reason,idempotency_key,request_hash)
                    SELECT gen_random_uuid()::text,organization_id,milestone_id,'CORRECTED',occurred_at,now(),
                     actor_user_id,id,'qualification','qualification-correct-'||gen_random_uuid()::text,'qualification'
                    FROM milestone_event WHERE id=:id"""), {"id": root})
    engine.dispose()
    print(f"STEP3A_POSTGRES_{args.scenario.upper()}=PASS")


if __name__ == "__main__":
    main()
