# Early smoke-test environment correction

An initial metadata smoke command supplied TESTING=True and DATABASE_URL for
SQLite but omitted the explicit SQLALCHEMY_DATABASE_URI configuration. The
repository's testing resolver correctly uses TEST_DATABASE_URL instead of
DATABASE_URL; an inherited setting selected the preconfigured local testing
database forwarder_auth_test at 127.0.0.1:5432. No credentials were printed.

create_all failed on an existing incompatible legacy route_stage_execution
foreign-key target. No test seed or Product command ran. SQLAlchemy's installed
Engine._run_ddl_visitor wraps the operation in Engine.begin(), so that failed
PostgreSQL DDL transaction rolls back; no follow-up query, cleanup, schema repair
or migration was attempted against that local test database.

The corrected smoke run explicitly sets both test/database environment selectors
and SQLALCHEMY_DATABASE_URI to sqlite:///:memory:, asserts that exact dialect/
database before create_all, and passes create/drop within its own memory database.
Subsequent P3-13 harnesses must set TEST_DATABASE_URL explicitly as well as the
ordinary URI; owned PostgreSQL tests must pass their owned URI explicitly.
This is diagnostic evidence, not a qualification PASS. No Production endpoint,
data or credential was requested or used.
