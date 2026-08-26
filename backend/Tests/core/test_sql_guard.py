import pytest

from src.sql_guard import DEFAULT_LIMIT, MAX_LIMIT, SqlGuardError, validate_select

ALLOWED = frozenset({"students", "teachers", "grades", "staff"})
ALLOWED_WITH_ADMISSION = ALLOWED | {"admission_applications"}


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


def test_strips_markdown_code_fence_before_parsing():
    sql = validate_select("```sql\nSELECT full_name FROM teachers\n```", ALLOWED)
    assert sql.startswith("SELECT")


def test_rejects_raw_student_names_by_default():
    with pytest.raises(SqlGuardError, match="персональные данные"):
        validate_select("SELECT full_name FROM students", ALLOWED)


def test_rejects_raw_student_names_via_table_alias():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT s.full_name FROM students s", ALLOWED)


def test_rejects_student_names_leaked_through_subquery():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT x FROM (SELECT full_name AS x FROM students) t", ALLOWED)


def test_rejects_star_over_sensitive_table():
    # SELECT * не содержит слова full_name, но развернётся в него при выполнении.
    with pytest.raises(SqlGuardError, match="SELECT \\*"):
        validate_select("SELECT * FROM students", ALLOWED)


def test_rejects_qualified_star_over_sensitive_table():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT s.* FROM students s", ALLOWED)


def test_allows_star_over_non_sensitive_table():
    sql = validate_select("SELECT * FROM teachers", ALLOWED)
    assert "LIMIT" in sql


def test_allows_raw_student_names_when_role_permits():
    sql = validate_select("SELECT full_name FROM students", ALLOWED, allow_raw_pii=True)
    assert "full_name" in sql


def test_allows_aggregated_student_names_even_without_pii_permission():
    sql = validate_select("SELECT count(full_name) FROM students", ALLOWED)
    assert "COUNT" in sql.upper()


def test_allows_filtering_by_pii_when_output_is_aggregated():
    # "сколько студентов на букву А" — раскрывает только число, никого не называет.
    sql = validate_select("SELECT count(*) FROM students WHERE full_name LIKE 'А%'", ALLOWED)
    assert "COUNT" in sql.upper()


def test_teacher_names_are_never_restricted():
    # full_name у teachers — не персональные данные студента, разрешено всегда.
    sql = validate_select("SELECT full_name FROM teachers", ALLOWED)
    assert "full_name" in sql


def test_student_cannot_filter_another_students_id():
    with pytest.raises(SqlGuardError, match="student_id"):
        validate_select(
            "SELECT grade FROM grades WHERE student_id = 99",
            ALLOWED,
            own_student_id=17,
        )


def test_student_can_filter_own_id():
    sql = validate_select(
        "SELECT grade FROM grades WHERE student_id = 17",
        ALLOWED,
        own_student_id=17,
    )
    assert "17" in sql


def test_student_cannot_use_in_list_with_others_id():
    with pytest.raises(SqlGuardError):
        validate_select(
            "SELECT grade FROM grades WHERE student_id IN (17, 18)",
            ALLOWED,
            own_student_id=17,
        )


def test_join_on_student_id_is_not_treated_as_lookup():
    sql = validate_select(
        "SELECT g.grade FROM grades g JOIN students s ON s.student_id = g.student_id "
        "WHERE g.student_id = 17",
        ALLOWED,
        own_student_id=17,
    )
    assert "LIMIT" in sql


def test_own_student_id_none_means_unrestricted():
    # staff/teacher/applicant — own_student_id не задан, проверка не действует.
    sql = validate_select("SELECT grade FROM grades WHERE student_id = 99", ALLOWED)
    assert "99" in sql
