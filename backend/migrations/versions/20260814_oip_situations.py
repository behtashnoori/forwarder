"""OIP-2 deterministic situations and attention projection.

Revision ID: 20260814_oip_situations
Revises: 20260813_mdpm_readiness
"""
from alembic import op
import sqlalchemy as sa

revision = "20260814_oip_situations"
down_revision = "20260813_mdpm_readiness"
branch_labels = None
depends_on = None

BIG = sa.BigInteger()

def upgrade():
    op.create_table("oip_situation",
        sa.Column("id",BIG,primary_key=True),sa.Column("public_id",sa.String(36),nullable=False,unique=True),
        sa.Column("organization_id",BIG,sa.ForeignKey("operational_organization.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("identity_key",sa.String(64),nullable=False),sa.Column("situation_type",sa.String(48),nullable=False),
        sa.Column("subject_type",sa.String(32),nullable=False),sa.Column("subject_public_id",sa.String(64),nullable=False),
        sa.Column("identity_dimensions",sa.JSON(),nullable=False),sa.Column("status",sa.String(20),nullable=False),
        sa.Column("severity",sa.String(16),nullable=False),sa.Column("urgency",sa.String(16),nullable=False),sa.Column("priority",sa.String(16),nullable=False),
        sa.Column("priority_explanation",sa.JSON(),nullable=False),sa.Column("first_detected_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("last_detected_at",sa.DateTime(timezone=True),nullable=False),sa.Column("last_changed_at",sa.DateTime(timezone=True),nullable=False),sa.Column("due_at",sa.DateTime(timezone=True)),
        sa.Column("assignee_user_id",BIG,sa.ForeignKey("expert_user.id",ondelete="SET NULL")),sa.Column("occurrence_count",sa.Integer(),nullable=False),
        sa.Column("policy_id",sa.String(40),nullable=False),sa.Column("policy_version",sa.String(32),nullable=False),sa.Column("projection_version",sa.String(32),nullable=False),
        sa.Column("calculated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("source_watermark",sa.String(160),nullable=False),sa.Column("freshness_status",sa.String(16),nullable=False),sa.Column("freshness_reason",sa.String(200)),
        sa.Column("snoozed_until",sa.DateTime(timezone=True)),sa.Column("disposition_reason",sa.Text()),sa.Column("acknowledged_at",sa.DateTime(timezone=True)),sa.Column("intervention_started_at",sa.DateTime(timezone=True)),sa.Column("resolved_at",sa.DateTime(timezone=True)),sa.Column("version",sa.Integer(),nullable=False),
        sa.UniqueConstraint("organization_id","identity_key",name="uq_oip_situation_identity"),sa.CheckConstraint("occurrence_count >= 1",name="ck_oip_situation_occurrence"),sa.CheckConstraint("version >= 1",name="ck_oip_situation_version"))
    op.create_index("ix_oip_attention_queue","oip_situation",["organization_id","status","priority","due_at"])
    op.create_table("oip_fact_reference",sa.Column("id",BIG,primary_key=True),sa.Column("public_id",sa.String(36),nullable=False,unique=True),sa.Column("organization_id",BIG,sa.ForeignKey("operational_organization.id",ondelete="RESTRICT"),nullable=False),sa.Column("source_domain",sa.String(40),nullable=False),sa.Column("source_type",sa.String(48),nullable=False),sa.Column("source_public_id",sa.String(64),nullable=False),sa.Column("subject_type",sa.String(32),nullable=False),sa.Column("subject_public_id",sa.String(64),nullable=False),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.Column("recorded_at",sa.DateTime(timezone=True)),sa.Column("source_version",sa.String(80),nullable=False),sa.Column("correlation_id",sa.String(100)),sa.Column("evidence_reference",sa.JSON(),nullable=False),sa.Column("validity",sa.String(16),nullable=False),sa.Column("superseded_by_public_id",sa.String(36)),sa.Column("resolved_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("organization_id","source_domain","source_type","source_public_id","source_version",name="uq_oip_fact_version"))
    op.create_table("oip_signal",sa.Column("id",BIG,primary_key=True),sa.Column("public_id",sa.String(36),nullable=False,unique=True),sa.Column("organization_id",BIG,sa.ForeignKey("operational_organization.id",ondelete="RESTRICT"),nullable=False),sa.Column("signal_type",sa.String(48),nullable=False),sa.Column("policy_id",sa.String(40),nullable=False),sa.Column("policy_version",sa.String(32),nullable=False),sa.Column("subject_type",sa.String(32),nullable=False),sa.Column("subject_public_id",sa.String(64),nullable=False),sa.Column("dedup_key",sa.String(64),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),sa.Column("derivation",sa.JSON(),nullable=False),sa.Column("observed_at",sa.DateTime(timezone=True),nullable=False),sa.Column("source_watermark",sa.String(160),nullable=False),sa.UniqueConstraint("organization_id","dedup_key","source_watermark",name="uq_oip_signal_observation"))
    op.create_table("oip_situation_evidence",sa.Column("situation_id",BIG,sa.ForeignKey("oip_situation.id",ondelete="CASCADE"),primary_key=True),sa.Column("fact_reference_id",BIG,sa.ForeignKey("oip_fact_reference.id",ondelete="RESTRICT"),primary_key=True),sa.Column("signal_id",BIG,sa.ForeignKey("oip_signal.id",ondelete="RESTRICT"),primary_key=True),sa.Column("is_current",sa.Boolean(),nullable=False),sa.Column("linked_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("oip_situation_history",sa.Column("id",BIG,primary_key=True),sa.Column("public_id",sa.String(36),nullable=False,unique=True),sa.Column("organization_id",BIG,sa.ForeignKey("operational_organization.id",ondelete="RESTRICT"),nullable=False),sa.Column("situation_id",BIG,sa.ForeignKey("oip_situation.id",ondelete="RESTRICT"),nullable=False),sa.Column("event_type",sa.String(32),nullable=False),sa.Column("from_status",sa.String(20)),sa.Column("to_status",sa.String(20),nullable=False),sa.Column("actor_user_id",BIG,sa.ForeignKey("expert_user.id",ondelete="RESTRICT")),sa.Column("reason",sa.Text()),sa.Column("metadata_json",sa.JSON(),nullable=False),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("oip_attention_projection",sa.Column("situation_id",BIG,sa.ForeignKey("oip_situation.id",ondelete="CASCADE"),primary_key=True),sa.Column("operational_work_item_id",BIG,sa.ForeignKey("operational_work_item.id",ondelete="SET NULL"),unique=True),sa.Column("calculated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("source_watermark",sa.String(160),nullable=False),sa.Column("projection_version",sa.String(32),nullable=False))
    op.create_table("oip_projection_state",sa.Column("organization_id",BIG,sa.ForeignKey("operational_organization.id",ondelete="CASCADE"),primary_key=True),sa.Column("status",sa.String(16),nullable=False),sa.Column("source_watermark",sa.String(160),nullable=False),sa.Column("projection_version",sa.String(32),nullable=False),sa.Column("calculated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("last_error",sa.Text()))

def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM oip_situation_history) OR EXISTS (SELECT 1 FROM oip_situation) THEN RAISE EXCEPTION 'cannot downgrade: durable OIP human-interaction evidence exists' USING ERRCODE='23503'; END IF; END $$""")
    for name in ("oip_projection_state","oip_attention_projection","oip_situation_history","oip_situation_evidence","oip_signal","oip_fact_reference","oip_situation"):
        op.drop_table(name)
