import jwt
import pytest

from src.auth import AuthError, create_token, decode_token


def test_round_trip_encodes_and_decodes_role():
    token = create_token(role="teacher", subject="ivanov")
    payload = decode_token(token)
    assert payload.role == "teacher"
    assert payload.subject == "ivanov"


def test_rejects_token_signed_with_wrong_secret():
    forged = jwt.encode({"sub": "x", "role": "staff"}, "не тот секрет", algorithm="HS256")
    with pytest.raises(AuthError):
        decode_token(forged)


def test_rejects_expired_token():
    from datetime import datetime, timedelta, timezone

    from src.auth import ALGORITHM, _secret

    expired = jwt.encode(
        {
            "sub": "x",
            "role": "staff",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        _secret(),
        algorithm=ALGORITHM,
    )
    with pytest.raises(AuthError, match="просрочен"):
        decode_token(expired)


def test_rejects_token_without_role():
    from src.auth import ALGORITHM, _secret

    no_role = jwt.encode({"sub": "x"}, _secret(), algorithm=ALGORITHM)
    with pytest.raises(AuthError):
        decode_token(no_role)


def test_extra_claims_round_trip():
    token = create_token(role="student", subject="petrov", student_id=17)
    payload = decode_token(token)
    assert payload.student_id == 17
    assert payload.teacher_id is None


def test_no_extra_claims_means_none():
    token = create_token(role="staff", subject="admin")
    payload = decode_token(token)
    assert payload.student_id is None
    assert payload.teacher_id is None
