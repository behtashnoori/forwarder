"""Step 3A occurrence decision lineage; historical event payloads stay immutable."""
from alembic import op
import sqlalchemy as sa

revision = "20260912_execution_authority"
down_revision = "20260911_project_cargo_preference"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("milestone_event", sa.Column("related_event_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_milestone_event_related", "milestone_event", "milestone_event",
                          ["related_event_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_milestone_event_related_event_id", "milestone_event", ["related_event_id"])
    if op.get_bind().dialect.name == "postgresql":
        # Add missing planning milestones only; no business event is fabricated.
        op.execute("""INSERT INTO operational_milestone
            (public_id, organization_id, operational_shipment_id, route_plan_id, route_leg_id,
             milestone_type, planned_at, projected_at, projected_state, verification_state,
             lifecycle_status, version, created_at, updated_at)
            SELECT gen_random_uuid()::text, s.organization_id, s.id, p.id, l.id,
              code, CASE WHEN code='departure' THEN l.planned_departure ELSE l.planned_arrival END,
              CASE WHEN code='departure' THEN l.planned_departure ELSE l.planned_arrival END,
              'planned', 'planned', 'PENDING', 1, now(), now()
            FROM route_leg l JOIN route_plan p ON p.id=l.route_plan_id
            JOIN operational_shipment s ON s.id=p.operational_shipment_id
            CROSS JOIN (VALUES ('departure'), ('arrival')) AS codes(code)
            WHERE NOT EXISTS (SELECT 1 FROM operational_milestone m
              WHERE m.route_leg_id=l.id AND m.milestone_type=code)""")
        op.execute("""
        CREATE FUNCTION public.step3a_validate_event_v1() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE target milestone_event%ROWTYPE; owner_org bigint;
        BEGIN
          SELECT organization_id INTO owner_org FROM operational_milestone WHERE id=NEW.milestone_id FOR UPDATE;
          IF NEW.organization_id IS DISTINCT FROM owner_org THEN
            RAISE EXCEPTION 'event organization mismatch' USING ERRCODE='23514';
          END IF;
          IF NEW.event_type IN ('verified','VERIFIED') THEN
            IF NEW.related_event_id IS NULL OR NEW.supersedes_event_id IS NOT NULL THEN
              RAISE EXCEPTION 'verification requires a decision reference' USING ERRCODE='23514';
            END IF;
          ELSIF NEW.related_event_id IS NOT NULL THEN
            RAISE EXCEPTION 'only verification may reference a decision target' USING ERRCODE='23514';
          END IF;
          IF NEW.supersedes_event_id IS NOT NULL AND NEW.event_type NOT IN ('corrected','CORRECTED') THEN
            RAISE EXCEPTION 'only correction may supersede an occurrence' USING ERRCODE='23514';
          END IF;
          IF NEW.related_event_id IS NOT NULL OR NEW.supersedes_event_id IS NOT NULL THEN
            SELECT * INTO target FROM milestone_event WHERE id=COALESCE(NEW.related_event_id,NEW.supersedes_event_id);
            IF NOT FOUND OR target.milestone_id<>NEW.milestone_id OR target.organization_id<>NEW.organization_id
               OR target.event_type NOT IN ('reported','corrected','CORRECTED') THEN
              RAISE EXCEPTION 'invalid occurrence target' USING ERRCODE='23514';
            END IF;
          END IF;
          IF NEW.event_type IN ('corrected','CORRECTED') AND EXISTS (
            SELECT 1 FROM milestone_event WHERE supersedes_event_id=NEW.supersedes_event_id
              AND event_type IN ('corrected','CORRECTED')) THEN
            RAISE EXCEPTION 'stale correction target' USING ERRCODE='23514';
          END IF;
          IF NEW.event_type='reported' AND (NEW.supersedes_event_id IS NOT NULL OR EXISTS (
            SELECT 1 FROM milestone_event WHERE milestone_id=NEW.milestone_id AND event_type='reported')) THEN
            RAISE EXCEPTION 'competing occurrence root' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_step3a_event_integrity BEFORE INSERT ON milestone_event
        FOR EACH ROW EXECUTE FUNCTION public.step3a_validate_event_v1();
        """)


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM milestone_event WHERE related_event_id IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Cannot discard retained verification decision lineage")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER trg_step3a_event_integrity ON milestone_event")
        op.execute("DROP FUNCTION public.step3a_validate_event_v1()")
    op.drop_index("ix_milestone_event_related_event_id", table_name="milestone_event")
    op.drop_constraint("fk_milestone_event_related", "milestone_event", type_="foreignkey")
    op.drop_column("milestone_event", "related_event_id")
