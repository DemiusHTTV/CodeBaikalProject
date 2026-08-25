"""Отправка запросов в GigaChat — и больше ничего.

Этот файл не знает, что такое SQL или схема БД. Он умеет ровно одну вещь:
отправить (system, user) в модель и вернуть текст ответа. Какой именно текст
слать — решает вызывающий код (см. src/ask.py), не этот файл.

Как это устроено:
1. GigaChat работает через два HTTP-адреса Сбера:
     OAUTH_URL — обменять ключ (.env: GIGACHAT_AUTH_KEY, GIGACHAT_SCOPE) на access_token;
     CHAT_URL  — отправить сообщения, получить ответ модели.
2. access_token живёт ~30 минут, поэтому мы держим его в памяти процесса
   (_cached_token) и запрашиваем заново только когда он истёк — иначе каждый
   вопрос пользователя стоил бы двух HTTP-запросов вместо одного.

Когда завтра появится новый ключ — меняешь только GIGACHAT_AUTH_KEY в .env,
в этом файле трогать нечего.
"""
from __future__ import annotations

import logging
import os
import time
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
MODEL_NAME = "GigaChat"

_cached_token: str | None = None
_cached_token_expires_at: float = 0.0


class LlmError(RuntimeError):
    """Модель недоступна или ответила не тем, что нужно."""


async def _get_access_token(client: httpx.AsyncClient) -> str:
    global _cached_token, _cached_token_expires_at

    if _cached_token and time.time() < _cached_token_expires_at:
        return _cached_token

    logger.info("Запрашиваю новый access_token у GigaChat")
    auth_key = os.environ["GIGACHAT_AUTH_KEY"]
    scope = os.environ["GIGACHAT_SCOPE"]

    response = await client.post(
        OAUTH_URL,
        headers={
            "Authorization": f"Basic {auth_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"scope": scope},
    )
    if response.status_code == 401:
        logger.error("GigaChat отклонил ключ (401)")
        raise LlmError(
            "GigaChat отклонил ключ (401). Проверь GIGACHAT_AUTH_KEY и GIGACHAT_SCOPE в .env."
        )
    response.raise_for_status()

    _cached_token = response.json()["access_token"]
    _cached_token_expires_at = time.time() + 25 * 60  # обновляем чуть раньше, чем протухнет
    logger.info("Новый access_token получен")
    return _cached_token


async def ask_llm(system_prompt: str, user_message: str, temperature: float = 0.0) -> str:
    """Отправляет один запрос модели (system + user) и возвращает текст её ответа."""
    logger.debug("Запрос к GigaChat: %s", user_message)
    # verify=False: сертификат GigaChat подписан УЦ Минцифры, которого нет в
    # системном хранилище доверенных сертификатов. Для прототипа — так, для
    # прода — подложить сертификат и убрать verify=False.
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        token = await _get_access_token(client)
        response = await client.post(
            CHAT_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model": MODEL_NAME,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            },
        )
    if response.status_code == 401:
        logger.error("GigaChat отклонил токен при отправке сообщения (401)")
        raise LlmError("GigaChat отклонил токен при отправке сообщения (401)")
    response.raise_for_status()

    choices = response.json().get("choices") or []
    if not choices:
        logger.error("GigaChat вернул пустой ответ")
        raise LlmError("GigaChat вернул пустой ответ")
    logger.debug("Ответ GigaChat получен")
    return choices[0]["message"]["content"]