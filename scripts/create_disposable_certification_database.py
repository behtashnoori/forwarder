"""Create the one explicitly named, loopback-only disposable certification DB."""
import os
import re
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = make_url(os.environ["CERT_ADMIN_URL"])
name = os.environ["CERT_DB_NAME"]
if url.get_backend_name() != "postgresql" or url.host not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit("refusing non-loopback PostgreSQL")
if not re.fullmatch(r"forwarder_integrated_cert_[a-z0-9_]+", name):
    raise SystemExit("refusing unsafe database name")
engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
with engine.connect() as connection:
    connection.execute(text("select pg_terminate_backend(pid) from pg_stat_activity where datname=:name and pid<>pg_backend_pid()"), {"name": name})
    connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}"')
    connection.exec_driver_sql(f'CREATE DATABASE "{name}" ENCODING \'UTF8\'')
engine.dispose()
print(f"created={name}")
