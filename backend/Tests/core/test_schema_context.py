from src.schema_context import build_schema_prompt, parse_tables, table_names

EXPECTED_TABLES = {
    "faculties",
    "departments",
    "directions",
    "groups_",
    "students",
    "teachers",
    "deans",
    "staff",
    "disciplines",
    "teacher_disciplines",
    "grades",
    "rooms",
    "schedule",
    "admission_applications",
}


def test_parse_tables_matches_schema_sql():
    assert table_names() == frozenset(EXPECTED_TABLES)


def test_sensitive_tables_flagged():
    tables = {t.name: t.sensitive for t in parse_tables()}
    assert tables["students"] is True
    assert tables["admission_applications"] is True
    assert tables["grades"] is True
    assert tables["teachers"] is False
    assert tables["staff"] is False


def test_columns_are_parsed():
    tables = {t.name: t for t in parse_tables()}
    student_columns = {c.name for c in tables["students"].columns}
    assert {"student_id", "full_name", "group_id", "admission_year"} == student_columns


def test_schema_prompt_mentions_pdn_note_for_sensitive_tables():
    prompt = build_schema_prompt()
    assert "students(" in prompt
    assert "персональные данные" in prompt
    assert "teachers(" in prompt
