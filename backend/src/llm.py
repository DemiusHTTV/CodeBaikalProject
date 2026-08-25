"""Отправка запросов в YandexGPT (Yandex Cloud Foundation Models) — и больше ничего.

Этот файл не знает, что такое SQL или схема БД. Он умеет ровно одну вещь:
отправить (system, user) в модель и вернуть текст ответа. Какой именно текст
слать — решает вызывающий код (см. src/ask.py), не этот файл.

Как это устроено:
1. Один HTTP-адрес — COMPLETION_URL — туда шлём сообщения, получаем ответ модели.
2. Авторизация — статичный API-ключ из .env (YANDEX_AUTH). Никакого обмена на
   временный токен не нужно (в отличие от GigaChat) — ключ идёт в заголовке
   Authorization: Api-Key <ключ> прямо на каждый запрос.
3. Какую модель спрашивать — указывается строкой modelUri вида
   gpt://<folder_id>/<модель>/<версия>, собирается из YANDEX_FOLDER + YANDEX_MODEL.

Понадобится сменить модель или ключ — правишь .env, в этом файле трогать нечего.
"""
from __future__ import annotations

import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


class LlmError(RuntimeError):
    """Модель недоступна или ответила не тем, что нужно."""


async def ask_llm(system_prompt: str, user_message: str, temperature: float = 0.0) -> str:
    """Отправляет один запрос модели (system + user) и возвращает текст её ответа."""
    auth_key = os.environ["YANDEX_AUTH"].strip()
    folder_id = os.environ["YANDEX_FOLDER"].strip()
    model = os.environ["YANDEX_MODEL"].strip()

    logger.debug("Запрос к Yandex: %s", user_message)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            COMPLETION_URL,
            headers={
                "Authorization": f"Api-Key {auth_key}",
                "x-folder-id": folder_id,
                "Content-Type": "application/json",
            },
            json={
                "modelUri": f"gpt://{folder_id}/{model}",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": "1000",
                },
                "messages": [
                    {"role": "system", "text": system_prompt},
                    {"role": "user", "text": user_message},
                ],
            },
        )

    if response.status_code == 401:
        logger.error("Yandex отклонил ключ (401)")
        raise LlmError("Yandex отклонил ключ (401). Проверь YANDEX_AUTH и YANDEX_FOLDER в .env.")
    response.raise_for_status()

    alternatives = response.json().get("result", {}).get("alternatives") or []
    if not alternatives:
        logger.error("Yandex вернул пустой ответ")
        raise LlmError("Yandex вернул пустой ответ")
    logger.debug("Ответ Yandex получен")
    return alternatives[0]["message"]["text"]
