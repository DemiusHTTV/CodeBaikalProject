import asyncio

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    # TestClient(app) запускает lifespan, а тот поднимает пул к БД — без неё
    # эндпоинты не проверить, поэтому тесты пропускаются, а не падают.
    try:
        with TestClient(app) as instance:
            yield instance
    except (OSError, asyncio.TimeoutError) as exc:
        pytest.skip(f"БД недоступна из этого окружения: {exc}")


def test_applicant_logs_in_without_credentials(client):
    response = client.post("/api/login", json={"role": "applicant"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "applicant"
    assert body["allow_raw_pii"] is False
    assert body["token"]


def test_applicant_has_no_access_to_student_tables(client):
    body = client.post("/api/login", json={"role": "applicant"}).json()
    assert "students" not in body["allowed_tables"]
    assert "grades" not in body["allowed_tables"]


def test_other_roles_require_credentials(client):
    response = client.post("/api/login", json={"role": "student"})
    assert response.status_code == 400


def test_rejects_wrong_password(client):
    response = client.post(
        "/api/login",
        json={"role": "student", "username": "student1", "password": "не тот"},
    )
    assert response.status_code == 401


def test_rejects_role_that_does_not_match_account(client):
    response = client.post(
        "/api/login",
        json={"role": "staff", "username": "student1", "password": "student12345"},
    )
    assert response.status_code == 403


def test_staff_login_grants_raw_pii(client):
    response = client.post(
        "/api/login",
        json={"role": "staff", "username": "staff1", "password": "staff12345"},
    )
    assert response.status_code == 200
    assert response.json()["allow_raw_pii"] is True


def test_ask_requires_token(client):
    response = client.post("/api/ask", json={"question": "сколько студентов"})
    assert response.status_code == 401


def test_ask_rejects_forged_token(client):
    response = client.post(
        "/api/ask",
        json={"question": "сколько студентов"},
        headers={"Authorization": "Bearer forged.token.value"},
    )
    assert response.status_code == 401


# Служебная таблица users не должна быть доступна ни одной роли — иначе через
# обычный вопрос можно было бы вытащить password_hash.
@pytest.mark.parametrize(
    "login_body",
    [
        {"role": "applicant"},
        {"role": "student", "username": "student1", "password": "student12345"},
        {"role": "staff", "username": "staff1", "password": "staff12345"},
    ],
)
def test_users_table_never_in_allowed_tables(client, login_body):
    body = client.post("/api/login", json=login_body).json()
    assert "users" not in body["allowed_tables"]
