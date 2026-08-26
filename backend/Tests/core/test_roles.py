import pytest

from src.roles import policy_for


def test_staff_sees_everything_including_raw_pii():
    policy = policy_for("staff")
    assert "students" in policy.allowed_tables
    assert "admission_applications" in policy.allowed_tables
    assert policy.allow_raw_pii is True


def test_student_cannot_see_raw_pii_or_admissions():
    policy = policy_for("student")
    assert policy.allow_raw_pii is False
    assert "admission_applications" not in policy.allowed_tables
    assert "students" in policy.allowed_tables  # свою успеваемость видит


def test_applicant_has_no_access_to_students_or_grades():
    policy = policy_for("applicant")
    assert "students" not in policy.allowed_tables
    assert "grades" not in policy.allowed_tables
    assert "directions" in policy.allowed_tables
    assert policy.allow_raw_pii is False


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        policy_for("superadmin")
