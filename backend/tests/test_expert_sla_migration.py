"""Disposable SQLite rehearsal for the expert SLA migration."""
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parents[2]


def _config(database_url: str) -> Config:
    config = Config(str(ROOT / "backend" / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_expert_sla_upgrade_constraints_and_downgrade(tmp_path):
    database = tmp_path / "expert-sla-migration.sqlite"
    url = f"sqlite:///{database.as_posix()}"
    config = _config(url)
    engine = sa.create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE expert_user ("
                "id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL, "
                "password_hash VARCHAR(128) NOT NULL, full_name VARCHAR(100) NOT NULL, "
                "role VARCHAR(20), is_active BOOLEAN, can_handle_domestic BOOLEAN NOT NULL, "
                "can_handle_international BOOLEAN NOT NULL, created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE alembic_version ("
                "version_num VARCHAR(255) NOT NULL PRIMARY KEY)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('20260802_expert_scope')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO expert_user "
                "(username, password_hash, full_name, role, is_active, "
                "can_handle_domestic, can_handle_international, created_at) "
                "VALUES ('existing', 'hash', 'Existing Expert', 'expert', 1, 1, 1, CURRENT_TIMESTAMP)"
            )
        )

    command.upgrade(config, "20260803_expert_sla")
    with engine.begin() as connection:
        assert connection.execute(
            sa.text("SELECT sla_response_work_minutes FROM expert_user")
        ).scalars().all() == [120]
        assert connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM expert_user "
                "WHERE sla_response_work_minutes IS NULL"
            )
        ).scalar_one() == 0
        for value in (0, 10081):
            with pytest.raises(sa.exc.IntegrityError):
                with connection.begin_nested():
                    connection.execute(
                        sa.text(
                            "UPDATE expert_user SET sla_response_work_minutes=:value"
                        ),
                        {"value": value},
                    )

    command.downgrade(config, "20260802_expert_scope")
    with engine.connect() as connection:
        inspector = sa.inspect(connection)
        columns = {column["name"] for column in inspector.get_columns("expert_user")}
        checks = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("expert_user")
        }
        assert "sla_response_work_minutes" not in columns
        assert "ck_expert_user_sla_response_work_minutes" not in checks

    assert ScriptDirectory.from_config(config).get_heads() == ["20260811_project_configuration"]
