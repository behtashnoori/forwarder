from scripts import release_postgres_orchestrator as runner


def test_inventory_is_unique_complete_and_isolated():
    suites = runner.CURRENT + runner.HISTORICAL
    assert len({suite.suite_id for suite in suites}) == len(suites)
    assert len({suite.prefix for suite in suites}) == len(suites)
    assert all(suite.classification in {
        "CURRENT_HEAD_MANDATORY", "CURRENT_HEAD_COMPATIBILITY_REQUIRED",
        "HISTORICAL_RELEASE_MANDATORY",
    } for suite in suites)
    paths = {path for suite in suites for path in suite.tests}
    required = {
        "backend/tests/test_phase0_2_current_head_compatibility_postgresql.py",
        "backend/tests/test_dms_current_head_compatibility_postgresql.py",
        "backend/tests/test_operational_vertical_slice_postgresql.py",
        "backend/tests/test_mdpm_races_postgresql.py",
        "backend/tests/test_oip_races_postgresql.py",
        "backend/tests/test_oip_rebuild_recovery_postgresql.py",
        "backend/tests/test_fe2_races_postgresql.py",
        "backend/tests/test_phase1b_safe_downgrade_postgresql.py",
    }
    assert required <= paths


def test_sanitizer_removes_credentials_and_tokens():
    value = runner.sanitize("postgresql://user:hunter2@localhost/db token=abc password=q")
    assert "hunter2" not in value and "abc" not in value and "password=q" not in value


def test_database_names_are_unique_and_safety_guarded(tmp_path):
    instance = object.__new__(runner.Orchestrator)
    instance.run_id = "20260809123456abcdef"
    names = [instance.database_name(suite.prefix) for suite in runner.CURRENT + runner.HISTORICAL]
    assert len(names) == len(set(names))
    assert all(runner.SAFE_NAME.fullmatch(name) for name in names)
