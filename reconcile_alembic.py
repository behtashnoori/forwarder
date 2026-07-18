from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask import current_app
from sqlalchemy import inspect, text

from backend import create_app
from backend.extensions import db


CURRENT_LEGACY_REVISION = "20250221_auto"
EXPAND_REVISION = "20260720_expand_reference_data_identity"
HEAD_REVISION = "20260725_add_tracking_location_reference"

EXPECTED_EXPAND_COLUMNS = {
    "country.effective_from",
    "country.effective_to",
    "country.source_organization",
    "country.source_reference",
    "country.source_version",
    "country.dataset_id",

    "province.country_id",
    "province.is_active",
    "province.effective_from",
    "province.effective_to",
    "province.source_organization",
    "province.source_reference",
    "province.source_version",
    "province.dataset_id",

    "county.code",
    "county.is_active",
    "county.effective_from",
    "county.effective_to",
    "county.source_organization",
    "county.source_reference",
    "county.source_version",
    "county.dataset_id",

    "iran_port.code",
    "iran_port.country_id",
    "iran_port.effective_from",
    "iran_port.effective_to",
    "iran_port.source_organization",
    "iran_port.source_reference",
    "iran_port.source_version",
    "iran_port.dataset_id",

    "city.code",
    "city.is_active",
    "city.effective_from",
    "city.effective_to",
    "city.source_organization",
    "city.source_version",
    "city.dataset_id",
    "city.source_reference",

    "port_province_mapping.is_preferred",
    "port_province_mapping.is_active",
    "port_province_mapping.effective_from",
    "port_province_mapping.effective_to",
    "port_province_mapping.source_organization",
    "port_province_mapping.source_reference",
    "port_province_mapping.source_version",
    "port_province_mapping.dataset_id",
    "port_province_mapping.updated_at",
}

ALLOWED_LEGACY_EXTRA_OPERATIONS = {
    "remove_table",
    "remove_column",
    "remove_index",
    "remove_constraint",
}


def get_missing_schema():
    inspector = inspect(db.engine)
    missing_tables = set()
    missing_columns = set()

    for table in db.metadata.sorted_tables:
        if table.name == "alembic_version":
            continue

        if not inspector.has_table(table.name, schema=table.schema):
            missing_tables.add(table.fullname)
            continue

        existing_columns = {
            column["name"]
            for column in inspector.get_columns(
                table.name,
                schema=table.schema,
            )
        }

        for column in table.columns:
            if column.name not in existing_columns:
                missing_columns.add(
                    f"{table.fullname}.{column.name}"
                )

    return missing_tables, missing_columns


def iter_operations(value):
    if (
        isinstance(value, tuple)
        and value
        and isinstance(value[0], str)
    ):
        yield value
        return

    if isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_operations(item)


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name == "alembic_version":
        return False
    return True


app = create_app(skip_startup=True)

with app.app_context():
    config = current_app.extensions["migrate"].migrate.get_config(
        "backend/migrations"
    )

    script = ScriptDirectory.from_config(config)

    expand_script = script.get_revision(EXPAND_REVISION)
    if expand_script is None:
        raise SystemExit(
            f"STOP: migration not found: {EXPAND_REVISION}"
        )

    expand_parent = expand_script.down_revision

    if not isinstance(expand_parent, str):
        raise SystemExit(
            f"STOP: unexpected expand parent: {expand_parent!r}"
        )

    heads = script.get_heads()

    if heads != [HEAD_REVISION]:
        raise SystemExit(
            f"STOP: unexpected Alembic head: {heads}"
        )

    with db.engine.connect() as connection:
        database = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

        versions = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all()

    if len(versions) != 1:
        raise SystemExit(
            f"STOP: unexpected Alembic versions: {versions}"
        )

    current_revision = versions[0]

    print("DATABASE:", database)
    print("CURRENT_REVISION:", current_revision)
    print("EXPAND_PARENT:", expand_parent)
    print("EXPAND_REVISION:", EXPAND_REVISION)
    print("TARGET_HEAD:", HEAD_REVISION)

    missing_tables, missing_columns = get_missing_schema()

    print("\nMISSING_TABLES:", sorted(missing_tables))
    print("MISSING_COLUMNS:", sorted(missing_columns))

    if missing_tables:
        raise SystemExit(
            "STOP: required model tables are missing. "
            "Alembic was not changed."
        )

    if current_revision == CURRENT_LEGACY_REVISION:
        if missing_columns != EXPECTED_EXPAND_COLUMNS:
            unexpected = missing_columns - EXPECTED_EXPAND_COLUMNS
            already_present = EXPECTED_EXPAND_COLUMNS - missing_columns

            print("\nUNEXPECTED_MISSING:", sorted(unexpected))
            print(
                "EXPECTED_BUT_ALREADY_PRESENT:",
                sorted(already_present),
            )

            raise SystemExit(
                "STOP: schema does not match the exact expected "
                "pre-expand state. Alembic was not changed."
            )

        print(
            "\nSchema exactly matches the expected "
            "pre-expand state."
        )

        print(
            "Stamping only to the parent of the official "
            "expand migration:",
            expand_parent,
        )

        command.stamp(
            config,
            expand_parent,
            purge=True,
        )

        print(
            "Running official migration:",
            EXPAND_REVISION,
        )

        command.upgrade(
            config,
            EXPAND_REVISION,
        )

    elif current_revision == expand_parent:
        print(
            "\nAlready stamped at expand parent. "
            "Running official expand migration."
        )

        command.upgrade(
            config,
            EXPAND_REVISION,
        )

    elif current_revision == EXPAND_REVISION:
        print(
            "\nExpand migration is already registered."
        )

    elif current_revision == HEAD_REVISION:
        print(
            "\nDatabase is already registered at head."
        )

    else:
        raise SystemExit(
            f"STOP: unsupported current revision: "
            f"{current_revision}"
        )

    missing_tables, missing_columns = get_missing_schema()

    if missing_tables or missing_columns:
        print("\nPOST_EXPAND_MISSING_TABLES:")
        for item in sorted(missing_tables):
            print(" -", item)

        print("\nPOST_EXPAND_MISSING_COLUMNS:")
        for item in sorted(missing_columns):
            print(" -", item)

        raise SystemExit(
            "STOP: official expand migration completed, "
            "but required schema is still incomplete."
        )

    inspector = inspect(db.engine)
    tracking_table_exists = inspector.has_table(
        "tracking_location_reference"
    )

    if not tracking_table_exists:
        print(
            "\nTracking table does not exist; "
            "running official migration to head."
        )

        command.upgrade(
            config,
            HEAD_REVISION,
        )

    else:
        print(
            "\nTracking table already exists. "
            "Verifying full model compatibility before stamping head."
        )

        with db.engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={
                    "compare_type": True,
                    "compare_server_default": False,
                    "include_object": include_object,
                },
            )

            differences = compare_metadata(
                context,
                db.metadata,
            )

        operations = list(iter_operations(differences))

        blocking_operations = [
            operation
            for operation in operations
            if operation[0]
            not in ALLOWED_LEGACY_EXTRA_OPERATIONS
        ]

        print("\nREMAINING_SCHEMA_DIFFERENCES:")
        for operation in operations:
            print(" -", repr(operation))

        if blocking_operations:
            print("\nBLOCKING_DIFFERENCES:")
            for operation in blocking_operations:
                print(" -", repr(operation))

            raise SystemExit(
                "STOP: schema still has required differences. "
                "Head was not stamped."
            )

        print(
            "\nOnly harmless additional legacy objects remain."
        )
        print(
            "Stamping tracking migration as already represented "
            "in the current schema."
        )

        command.stamp(
            config,
            HEAD_REVISION,
            purge=True,
        )

    with db.engine.connect() as connection:
        final_versions = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all()

    if final_versions != [HEAD_REVISION]:
        raise SystemExit(
            f"STOP: final revision mismatch: {final_versions}"
        )

    final_missing_tables, final_missing_columns = (
        get_missing_schema()
    )

    if final_missing_tables or final_missing_columns:
        raise SystemExit(
            "STOP: final model schema verification failed."
        )

    print("\nSCHEMA_REPAIR_OK")
    print("FINAL_ALEMBIC_VERSION:", final_versions)