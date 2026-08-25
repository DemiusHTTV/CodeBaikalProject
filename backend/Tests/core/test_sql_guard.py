import pytest

from src.sql_guard import DEFAULT_LIMIT, MAX_LIMIT, SqlGuardError, validate_select

ALLOWED = frozenset({"students", "teachers", "grades", "staff"})


def test_adds_default_limit_when_missing():
    sql = validate_select("SELECT full_name FROM teachers", ALLOWED)
    assert f"LIMIT {DEFAULT_LIMIT}" in sql


def test_keeps_limit_within_max():
    sql = validate_select("SELECT full_name FROM teachers LIMIT 50", ALLOWED)
    assert "LIMIT 50" in sql


def test_caps_limit_above_max():
    sql = validate_select("SELECT full_name FROM teachers LIMIT 999999", ALLOWED)
    assert f"LIMIT {MAX_LIMIT}" in sql


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO teachers (full_name) VALUES ('x')",
        "UPDATE teachers SET full_name = 'x'",
        "DELETE FROM teachers",
        "DROP TABLE teachers",
        "ALTER TABLE teachers ADD COLUMN x TEXT",
        "TRUNCATE teachers",
    ],
)
def test_rejects_non_select_statements(sql):
    with pytest.raises(SqlGuardError):
        validate_select(sql, ALLOWED)


def test_rejects_stacked_statements():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT * FROM teachers; DROP TABLE teachers;", ALLOWED)


def test_rejects_table_outside_whitelist():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT * FROM admission_applications", ALLOWED)


def test_rejects_select_into():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT * INTO new_table FROM teachers", ALLOWED)


def test_rejects_row_locking():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT * FROM teachers FOR UPDATE", ALLOWED)


def test_rejects_forbidden_function():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT pg_sleep(10)", ALLOWED)


def test_rejects_file_access_function():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT * FROM pg_read_file('/etc/passwd')", ALLOWED)


def test_rejects_unparseable_sql():
    with pytest.raises(SqlGuardError):
        validate_select("select 1) union select pg_sleep(10) --", ALLOWED)


def test_allows_cte_referencing_only_whitelisted_tables():
    sql = validate_select(
        "WITH t AS (SELECT student_id FROM students) SELECT * FROM t",
        ALLOWED,
    )
    assert "LIMIT" in sql


def test_rejects_cte_referencing_disallowed_table():
    with pytest.raises(SqlGuardError):
        validate_select(
            "WITH t AS (SELECT * FROM admission_applications) SELECT * FROM t",
            ALLOWED,
        )


def test_table_check_is_case_insensitive():
    sql = validate_select("SELECT * FROM TEACHERS", ALLOWED)
    assert "LIMIT" in sql


def test_rejects_empty_sql():
    with pytest.raises(SqlGuardError):
        validate_select("   ", ALLOWED)


def test_rejects_write_hidden_inside_cte():
    with pytest.raises(SqlGuardError):
        validate_select(
            "WITH x AS (DELETE FROM grades RETURNING *) SELECT * FROM x",
            ALLOWED,
        )


def test_rejects_row_lock_hidden_inside_subquery():
    with pytest.raises(SqlGuardError):
        validate_select(
            "SELECT * FROM (SELECT * FROM teachers FOR UPDATE) t",
            ALLOWED,
        )


def test_non_numeric_limit_falls_back_to_default_instead_of_crashing():
    sql = validate_select("SELECT * FROM teachers LIMIT $1", ALLOWED)
    assert f"LIMIT {DEFAULT_LIMIT}" in sql
