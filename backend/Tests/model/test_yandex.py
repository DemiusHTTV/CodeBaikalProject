import os

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()

AUTH = os.getenv("YANDEX_AUTH")
FOLDER = os.getenv("YANDEX_FOLDER")
MODEL = os.getenv("YANDEX_MODEL")


@pytest.mark.asyncio
async def test_yandexgpt_completion_accessible():
    if not (AUTH and FOLDER and MODEL):
        pytest.skip("YANDEX_AUTH / YANDEX_FOLDER / YANDEX_MODEL не заданы в .env")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers={
                "Authorization": f"Api-Key {AUTH.strip()}",
                "x-folder-id": FOLDER.strip(),
                "Content-Type": "application/json",
            },
            json={
                "modelUri": f"gpt://{FOLDER.strip()}/{MODEL.strip()}",
                "completionOptions": {"stream": False, "temperature": 0.0, "maxTokens": "10"},
                "messages": [{"role": "user", "text": "Привет"}],
            },
        )
        response.raise_for_status()

    alternatives = response.json()["result"]["alternatives"]
    assert alternatives
    assert alternatives[0]["message"]["text"]
