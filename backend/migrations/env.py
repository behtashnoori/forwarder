"""Alembic environment configuration."""
import os
import sys
from logging.config import fileConfig

from alembic import context
from alembic.script import ScriptDirectory
from sqlalchemy import engine_from_config, pool

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app
from backend.extensions import db
from backend.migrations.version_table import ensure_version_table_capacity

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = db.metadata
script_directory = ScriptDirectory.from_config(config)


def _valid_parallel_heads(revisions: tuple[str, ...]) -> bool:
    """Accept only resolvable revisions that are mutually current branch heads."""
    try:
        current = script_directory.get_all_current(revisions)
    except Exception:
        return False
    return {revision.revision for revision in current} == set(revisions)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Get database URL from Flask app config. Use current_app when already in app context (e.g. run from startup.run_migrations) to avoid recursion."""
    try:
        from flask import current_app
        return current_app.config.get("SQLALCHEMY_DATABASE_URI")
    except RuntimeError:
        pass
    app = create_app(skip_startup=True)
    with app.app_context():
        return app.config.get("SQLALCHEMY_DATABASE_URI")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        with connection.begin():
            ensure_version_table_capacity(
                connection,
                multiple_revision_validator=_valid_parallel_heads,
            )

        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()







