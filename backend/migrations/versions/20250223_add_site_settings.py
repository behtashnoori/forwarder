"""Add site_settings table for configurable site content and logo.

Revision ID: 20250223_site_settings
Revises: 20250221_auto
Create Date: 2025-02-23

"""
from alembic import op
import sqlalchemy as sa

revision = "20250223_site_settings"
down_revision = "20250221_auto"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_settings",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("tagline", sa.String(length=200), nullable=True),
        sa.Column("footer_description", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=100), nullable=True),
        sa.Column("contact_address", sa.String(length=300), nullable=True),
        sa.Column("working_hours_weekdays", sa.String(length=100), nullable=True),
        sa.Column("working_hours_thursday", sa.String(length=100), nullable=True),
        sa.Column("support_text", sa.String(length=200), nullable=True),
        sa.Column("copyright_text", sa.String(length=300), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Single row with default Persian text
    conn = op.get_bind()
    default_footer = "ارائه دهنده خدمات حمل و نقل و فورواردری با بیش از ۱۰ سال تجربه در سراسر کشور"
    default_copyright = "© ۱۴۰۳ فورواردری سریع. تمامی حقوق محفوظ است."
    if conn.dialect.name == "sqlite":
        op.execute(
            f"""INSERT INTO site_settings (
                id, company_name, tagline, footer_description,
                contact_phone, contact_email, contact_address,
                working_hours_weekdays, working_hours_thursday, support_text,
                copyright_text, logo_url, updated_at
            ) VALUES (
                1, 'فورواردری سریع', 'ارسال آسان و مطمئن', '{default_footer.replace("'", "''")}',
                '۰۲۱-۸۸۷۷۶۶۵۵', 'info@forwarding.ir', 'تهران، میدان آزادی',
                'شنبه تا چهارشنبه: ۸-۱۸', 'پنج‌شنبه: ۸-۱۶', 'پشتیبانی ۲۴ ساعته',
                '{default_copyright.replace("'", "''")}', NULL, datetime('now')
            )"""
        )
    else:
        op.execute(
            sa.text("""
                INSERT INTO site_settings (
                    id, company_name, tagline, footer_description,
                    contact_phone, contact_email, contact_address,
                    working_hours_weekdays, working_hours_thursday, support_text,
                    copyright_text, logo_url, updated_at
                ) VALUES (
                    1, 'فورواردری سریع', 'ارسال آسان و مطمئن', :fd,
                    '۰۲۱-۸۸۷۷۶۶۵۵', 'info@forwarding.ir', 'تهران، میدان آزادی',
                    'شنبه تا چهارشنبه: ۸-۱۸', 'پنج‌شنبه: ۸-۱۶', 'پشتیبانی ۲۴ ساعته',
                    :cr, NULL, NOW()
                )
            """).bindparams(fd=default_footer, cr=default_copyright),
        )


def downgrade():
    op.drop_table("site_settings")
