"""Seed Iran and curated China-Iran tracking reference data.

Revision ID: 20260726_seed_iran_tracking_reference
Revises: 20260725_add_tracking_location_reference
"""

from alembic import op
import sqlalchemy as sa


revision = "20260726_seed_iran_tracking_reference"
down_revision = "20260725_add_tracking_location_reference"
branch_labels = None
depends_on = None


TRACKING_ROWS = [('cn-shanghai', 'شانگهای', 'Shanghai', 'CN', 'seaport', []),
 ('cn-ningbo-zhoushan', 'نینگبو-ژوشان', 'Ningbo-Zhoushan', 'CN', 'seaport', []),
 ('cn-shenzhen-yantian', 'شنژن / یانتیان', 'Shenzhen / Yantian', 'CN', 'seaport', []),
 ('cn-guangzhou-nansha', 'گوانگژو / نانشا', 'Guangzhou / Nansha', 'CN', 'seaport', []),
 ('cn-qingdao', 'چینگدائو', 'Qingdao', 'CN', 'seaport', []),
 ('cn-tianjin-xingang', 'تیانجین / شینگانگ', 'Tianjin / Xingang', 'CN', 'seaport', []),
 ('cn-lianyungang', 'لیانیونگانگ', 'Lianyungang', 'CN', 'rail_terminal', []),
 ('cn-yiwu', 'ایوو', 'Yiwu', 'CN', 'commercial_hub', ['Yiwu', 'ایوو', 'یی\u200cوو', 'یی وو']),
 ('cn-xian', 'شی\u200cآن', "Xi'an", 'CN', 'rail_terminal', ["Xi'an", 'Xian', 'شی\u200cآن', 'شیان']),
 ('cn-zhengzhou', 'ژنگژو', 'Zhengzhou', 'CN', 'rail_terminal', []),
 ('cn-chengdu', 'چنگدو', 'Chengdu', 'CN', 'rail_terminal', []),
 ('cn-chongqing', 'چونگ\u200cچینگ', 'Chongqing', 'CN', 'rail_terminal', []),
 ('cn-wuhan', 'ووهان', 'Wuhan', 'CN', 'rail_terminal', []),
 ('cn-lanzhou', 'لانژو', 'Lanzhou', 'CN', 'rail_terminal', []),
 ('cn-urumqi', 'اورومچی', 'Urumqi', 'CN', 'transit_city', []),
 ('cn-kashgar', 'کاشغر', 'Kashgar', 'CN', 'transit_city', []),
 ('cn-alashankou', 'آلاشانکو', 'Alashankou', 'CN', 'border_point', []),
 ('cn-khorgos', 'خورگوس', 'Khorgos', 'CN', 'border_point', []),
 ('kz-dostyk', 'دوستیک', 'Dostyk', 'KZ', 'border_point', []),
 ('kz-altynkol', 'آلتین\u200cکول', 'Altynkol', 'KZ', 'border_point', []),
 ('kz-almaty', 'آلماتی', 'Almaty', 'KZ', 'transit_city', []),
 ('kz-shymkent', 'شیمکنت', 'Shymkent', 'KZ', 'transit_city', []),
 ('KG-OSH', 'اوش', 'Osh', 'KG', 'commercial_hub', ['Osh', 'Ош', 'اوش']),
 ('uz-tashkent', 'تاشکند', 'Tashkent', 'UZ', 'transit_city', []),
 ('uz-samarkand', 'سمرقند', 'Samarkand', 'UZ', 'transit_city', []),
 ('uz-navoi', 'نوایی', 'Navoi', 'UZ', 'transit_city', []),
 ('uz-bukhara', 'بخارا', 'Bukhara', 'UZ', 'transit_city', []),
 ('tm-alat', 'آلات', 'Alat', 'TM', 'border_point', []),
 ('tm-farap', 'فاراپ', 'Farap', 'TM', 'border_point', []),
 ('tm-turkmenabat', 'ترکمن\u200cآباد', 'Turkmenabat', 'TM', 'transit_city', []),
 ('tm-mary', 'مرو', 'Mary', 'TM', 'transit_city', []),
 ('tm-tejen', 'تجن', 'Tejen', 'TM', 'transit_city', []),
 ('tm-serakhs', 'سرخس ترکمنستان', 'Serakhs', 'TM', 'border_point', []),
 ('tm-etrek', 'اترک', 'Etrek', 'TM', 'border_point', []),
 ('kz-aktau', 'آکتائو', 'Aktau', 'KZ', 'seaport', []),
 ('tm-turkmenbashi', 'ترکمن\u200cباشی', 'Turkmenbashi', 'TM', 'seaport', []),
 ('pk-sost', 'سوست', 'Sost', 'PK', 'border_point', []),
 ('pk-islamabad', 'اسلام\u200cآباد', 'Islamabad', 'PK', 'transit_city', []),
 ('pk-quetta', 'کویته', 'Quetta', 'PK', 'transit_city', []),
 ('pk-taftan', 'تفتان', 'Taftan', 'PK', 'border_point', []),
 ('pk-karachi', 'کراچی', 'Karachi', 'PK', 'seaport', []),
 ('pk-port-qasim', 'بندر قاسم', 'Port Qasim', 'PK', 'seaport', []),
 ('pk-gwadar', 'گوادر', 'Gwadar', 'PK', 'seaport', []),
 ('pk-gabd', 'گبد', 'Gabd', 'PK', 'border_point', []),
 ('af-herat', 'هرات', 'Herat', 'AF', 'transit_city', []),
 ('af-islam-qala', 'اسلام\u200cقلعه', 'Islam Qala', 'AF', 'border_point', []),
 ('af-zaranj', 'زرنج', 'Zaranj', 'AF', 'border_point', []),
 ('ir-sarakhs', 'سرخس', 'Sarakhs', 'IR', 'iran_gateway', []),
 ('ir-incheh-borun', 'اینچه\u200cبرون', 'Incheh Borun', 'IR', 'iran_gateway', []),
 ('ir-mirjaveh', 'میرجاوه', 'Mirjaveh', 'IR', 'iran_gateway', []),
 ('ir-dogharoun', 'دوغارون', 'Dogharoun', 'IR', 'iran_gateway', []),
 ('ir-rimdan', 'ریمدان', 'Rimdan', 'IR', 'iran_gateway', []),
 ('ir-mashhad', 'مشهد', 'Mashhad', 'IR', 'destination_city', []),
 ('ir-zahedan', 'زاهدان', 'Zahedan', 'IR', 'destination_city', []),
 ('ir-tehran', 'تهران', 'Tehran', 'IR', 'destination_city', []),
 ('ir-qom', 'قم', 'Qom', 'IR', 'destination_city', []),
 ('ir-isfahan', 'اصفهان', 'Isfahan', 'IR', 'destination_city', []),
 ('ir-yazd', 'یزد', 'Yazd', 'IR', 'destination_city', []),
 ('ir-kerman', 'کرمان', 'Kerman', 'IR', 'destination_city', []),
 ('ir-shahid-rajaee', 'بندر شهید رجایی', 'Shahid Rajaee Port', 'IR', 'iran_gateway', []),
 ('ir-chabahar', 'بندر چابهار', 'Chabahar Port', 'IR', 'iran_gateway', []),
 ('ir-imam-khomeini', 'بندر امام خمینی', 'Imam Khomeini Port', 'IR', 'iran_gateway', []),
 ('ir-amirabad', 'بندر امیرآباد', 'Amirabad Port', 'IR', 'iran_gateway', []),
 ('ir-anzali-caspian', 'بندر انزلی / کاسپین', 'Anzali / Caspian Port', 'IR', 'iran_gateway', [])]

NOTES = {'KG-OSH': 'هاب ترانزیتی جاده\u200cای و ریلی در جنوب قرقیزستان؛ قابل استفاده در گزارش\u200cهای دستی ردیابی '
           'محموله\u200cهای مسیر چین به ایران.'}


country = sa.table(
    "country",
    sa.column("id", sa.BigInteger()),
    sa.column("name_en", sa.String()),
    sa.column("name_fa", sa.String()),
    sa.column("code", sa.String()),
    sa.column("is_active", sa.Boolean()),
    sa.column("created_at", sa.DateTime()),
)


tracking_location_reference = sa.table(
    "tracking_location_reference",
    sa.column("id", sa.BigInteger()),
    sa.column("internal_key", sa.String()),
    sa.column("name_fa", sa.String()),
    sa.column("name_en", sa.String()),
    sa.column("country_code", sa.String()),
    sa.column("location_type", sa.String()),
    sa.column("aliases", sa.JSON()),
    sa.column("reference_status", sa.String()),
    sa.column("sort_order", sa.Integer()),
    sa.column("is_active", sa.Boolean()),
    sa.column("notes", sa.Text()),
    sa.column("created_at", sa.DateTime()),
    sa.column("updated_at", sa.DateTime()),
)


def _upsert_iran_country(bind):
    matches = bind.execute(
        sa.select(
            country.c.id,
            country.c.code,
            country.c.name_en,
            country.c.name_fa,
        ).where(
            sa.or_(
                sa.func.upper(sa.func.coalesce(country.c.code, ""))
                .in_(["IR", "IRN"]),
                sa.func.lower(
                    sa.func.coalesce(country.c.name_en, "")
                ) == "iran",
                sa.func.coalesce(country.c.name_fa, "") == "\u0627\u06cc\u0631\u0627\u0646",
            )
        )
    ).mappings().all()

    if len(matches) > 1:
        raise RuntimeError(
            "Ambiguous Iran country records found; "
            "manual reconciliation is required."
        )

    values = {
        "name_en": "Iran",
        "name_fa": "\u0627\u06cc\u0631\u0627\u0646",
        "code": "IR",
        "is_active": True,
    }

    if matches:
        bind.execute(
            sa.update(country)
            .where(country.c.id == matches[0]["id"])
            .values(**values)
        )
        return

    bind.execute(
        sa.insert(country).values(
            **values,
            created_at=sa.func.now(),
        )
    )


def _upsert_tracking_locations(bind):
    for sort_order, row_data in enumerate(TRACKING_ROWS):
        (
            internal_key,
            name_fa,
            name_en,
            country_code,
            location_type,
            aliases,
        ) = row_data

        existing_id = bind.execute(
            sa.select(tracking_location_reference.c.id).where(
                tracking_location_reference.c.internal_key
                == internal_key
            )
        ).scalar_one_or_none()

        values = {
            "name_fa": name_fa,
            "name_en": name_en,
            "country_code": country_code,
            "location_type": location_type,
            "aliases": aliases,
            "reference_status": "internal_reference",
            "sort_order": sort_order,
            "is_active": True,
            "notes": NOTES.get(internal_key),
            "updated_at": sa.func.now(),
        }

        if existing_id is None:
            bind.execute(
                sa.insert(tracking_location_reference).values(
                    internal_key=internal_key,
                    created_at=sa.func.now(),
                    **values,
                )
            )
            continue

        bind.execute(
            sa.update(tracking_location_reference)
            .where(
                tracking_location_reference.c.id == existing_id
            )
            .values(**values)
        )


def upgrade():
    bind = op.get_bind()

    _upsert_iran_country(bind)
    _upsert_tracking_locations(bind)


def downgrade():
    # Intentional no-op:
    # Reference rows may already be used by operational tracking records.
    # Automatically deleting or reverting them would risk data integrity.
    pass
