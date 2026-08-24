import os
import uuid

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()

AUTH = os.getenv("GIGACHAT_AUTH_KEY")
SCOPE = os.getenv("GIGACHAT_SCOPE")


@pytest.mark.asyncio
async def test_gigachat_models_accessible():
    if not AUTH or not SCOPE:
        pytest.skip("GIGACHAT_AUTH_KEY / GIGACHAT_SCOPE не заданы в .env")

    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        auth_response = await client.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={
                "Authorization": f"Basic {AUTH}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"scope": SCOPE},
        )
        auth_response.raise_for_status()
        token = auth_response.json()["access_token"]

        models_response = await client.get(
            "https://gigachat.devices.sberbank.ru/api/v1/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        models_response.raise_for_status()

        model_ids = [m["id"] for m in models_response.json()["data"]]
        assert model_ids
