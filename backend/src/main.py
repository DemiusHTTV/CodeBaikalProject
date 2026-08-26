"""HTTP API ассистента.

Запуск (из backend/):
    .venv/bin/uvicorn src.main:app --reload

Две ручки:
    POST /api/login  {"role": "student", "student_id": 1}  -> {"token": "..."}
    POST /api/ask    {"question": "..."}  + заголовок Authorization: Bearer <token>

Роль берётся ТОЛЬКО из подписанного токена, никогда из тела запроса — иначе
клиент мог бы просто прислать "role": "staff" и получить чужие права.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db
from .auth import AuthError, TokenPayload, create_token, decode_token
from .llm import LlmError
from .logging_config import setup_logging
from .pipeline import answer_question
from .roles import policy_for

logger = logging.getLogger(__name__)

ROLES = ("applicant", "student", "teacher", "staff")


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
    student_id: int | None = None


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


@app.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    if request.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Неизвестная роль. Доступны: {', '.join(ROLES)}")

    extra = {}
    if request.role == "student":
        # Без student_id роль student не смогла бы спросить "мои оценки",
        # а own_rows-проверка не знала бы, чьи данные считать своими.
        extra["student_id"] = request.student_id if request.student_id is not None else 1

    token = create_token(role=request.role, subject="демо-пользователь", **extra)
    policy = policy_for(request.role)
    logger.info("Выдан токен для роли %s", request.role)
    return LoginResponse(
        token=token,
        role=request.role,
        allowed_tables=sorted(policy.allowed_tables),
        allow_raw_pii=policy.allow_raw_pii,
    )


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest, user: TokenPayload = Depends(current_user)) -> AskResponse:
    policy = policy_for(user.role)
    try:
        result = await answer_question(request.question, policy, user.student_id)
    except LlmError as exc:
        logger.error("Модель недоступна: %s", exc)
        raise HTTPException(status_code=502, detail=f"Модель недоступна: {exc}") from exc

    return AskResponse(**vars(result))


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
