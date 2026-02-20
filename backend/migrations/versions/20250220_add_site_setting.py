"""Add site_setting table for admin-editable site content.

Revision ID: 20250220_add_site_setting
Revises: 20250220_merge_final
Create Date: 2025-02-20

"""
from alembic import op
import sqlalchemy as sa


revision = "20250220_add_site_setting"
down_revision = "20250220_merge_final"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_setting",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_site_setting_key"),
    )
    op.create_index(op.f("ix_site_setting_key"), "site_setting", ["key"], unique=True)

    # Seed default values
    conn = op.get_bind()
    defaults = [
        ("site_name", "فورواردری سریع"),
        ("site_tagline", "ارائه دهنده خدمات حمل و نقل و فورواردری با بیش از ۱۰ سال تجربه در سراسر کشور"),
        ("contact_phone", "۰۲۱-۸۸۷۷۶۶۵۵"),
        ("contact_email", "info@forwarding.ir"),
        ("contact_address", "تهران، میدان آزادی"),
        ("working_hours_week", "شنبه تا چهارشنبه: ۸-۱۸"),
        ("working_hours_thu", "پنج‌شنبه: ۸-۱۶"),
        ("support_text", "پشتیبانی ۲۴ ساعته"),
        ("copyright_text", "© ۱۴۰۳ فورواردری سریع. تمامی حقوق محفوظ است."),
        ("show_contact_section", "1"),
        ("show_working_hours_section", "1"),
        ("show_footer", "1"),
    ]
    for k, v in defaults:
        conn.execute(sa.text("INSERT INTO site_setting (key, value, updated_at) VALUES (:k, :v, CURRENT_TIMESTAMP)"), {"k": k, "v": v})


def downgrade() -> None:
    op.drop_index(op.f("ix_site_setting_key"), table_name="site_setting")
    op.drop_table("site_setting")
