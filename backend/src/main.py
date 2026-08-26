"""HTTP API ассистента.

Запуск (из backend/):
    .venv/bin/uvicorn src.main:app --reload

Две ручки:
    POST /api/login  {"role": "student", "username": "student1", "password": "..."}
                     -> {"token": "..."}
                     роль applicant — анонимная, логин/пароль не нужны
    POST /api/ask    {"question": "..."}  + заголовок Authorization: Bearer <token>

Роль и student_id/teacher_id берутся из таблицы users по логину/паролю и
кладутся в подписанный токен — клиент никогда не присылает роль сам, иначе
мог бы прислать "role": "staff" и получить чужие права.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db
from .analytics import load_events, summarize
from .auth import AuthError, TokenPayload, create_token, decode_token
from .llm import LlmError
from .logging_config import setup_logging
from .pipeline import answer_question
from .roles import policy_for
from .users import verify_credentials

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await db.init_pool()
    logger.info("API запущен")
    yield
    await db.close_pool()
    logger.info("API остановлен")


app = FastAPI(title="Ассистент университета", lifespan=lifespan)

# Фронт живёт на другом порту (Vite: 5173), браузер без этого не пустит запросы.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    role: str
    # Пусто только для роли applicant — она анонимная, см. login().
    username: str | None = None
    password: str | None = None


class LoginResponse(BaseModel):
    token: str
    role: str
    allowed_tables: list[str]
    allow_raw_pii: bool


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AskResponse(BaseModel):
    question: str
    sql: str | None = None
    columns: list[str] = []
    rows: list[list] = []
    row_count: int = 0
    answer: str | None = None  # человеческий пересказ таблицы
    error: str | None = None
    error_kind: str | None = None
    elapsed_ms: int = 0


async def current_user(authorization: str = Header(default="")) -> TokenPayload:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Нужен заголовок Authorization: Bearer <токен>")
    try:
        return decode_token(authorization.removeprefix("Bearer ").strip())
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _login_response(role: str, token: str) -> LoginResponse:
    policy = policy_for(role)
    return LoginResponse(
        token=token,
        role=role,
        allowed_tables=sorted(policy.allowed_tables),
        allow_raw_pii=policy.allow_raw_pii,
    )


@app.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    # Абитуриент — анонимная роль: аккаунта в университете у него ещё нет, а
    # доступны ему только справочные данные о наборе (см. roles.py), поэтому
    # логин/пароль не спрашиваем. Права всё равно ограничены политикой роли.
    if request.role == "applicant":
        logger.info("Выдан токен анонимному абитуриенту")
        return _login_response(
            "applicant", create_token(role="applicant", subject="анонимный абитуриент")
        )

    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="Нужны логин и пароль")

    user = await verify_credentials(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    # Роль с формы — только сверка с тем, что записано у пользователя в БД.
    # В токен ниже всё равно идёт user.role, а не request.role: иначе клиент
    # мог бы прислать "staff" и получить чужие права.
    if user.role != request.role:
        logger.warning(
            "Роль не совпала: пользователь %s имеет роль %s, выбрана %s",
            user.username,
            user.role,
            request.role,
        )
        raise HTTPException(
            status_code=403,
            detail="Этот аккаунт относится к другой роли — выберите нужную роль и попробуйте снова",
        )

    extra = {}
    if user.student_id is not None:
        extra["student_id"] = user.student_id
    if user.teacher_id is not None:
        extra["teacher_id"] = user.teacher_id

    logger.info("Выдан токен для роли %s (пользователь %s)", user.role, user.username)
    return _login_response(user.role, create_token(role=user.role, subject=user.username, **extra))


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest, user: TokenPayload = Depends(current_user)) -> AskResponse:
    policy = policy_for(user.role)
    try:
        result = await answer_question(request.question, policy, user.student_id, role=user.role)
    except LlmError as exc:
        logger.error("Модель недоступна: %s", exc)
        raise HTTPException(status_code=502, detail=f"Модель недоступна: {exc}") from exc

    return AskResponse(**vars(result))


@app.get("/api/analytics")
async def analytics(user: TokenPayload = Depends(current_user)) -> dict:
    # В логе лежат вопросы всех пользователей — отдаём только администрации.
    if user.role != "staff":
        raise HTTPException(status_code=403, detail="Аналитика доступна только сотрудникам")
    logger.info("Запрошена аналитика", extra={"event": {"role": user.role}})
    return summarize(load_events())


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
