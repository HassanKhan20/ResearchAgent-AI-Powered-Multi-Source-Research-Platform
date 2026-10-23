import os
import tempfile

_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db}"
os.environ["OFFLINE_MODE"] = "true"
os.environ["REDIS_URL"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
async def client():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth(client):
    resp = await client.post("/api/sessions", json={"display_name": "Tester"})
    return {"Authorization": f"Bearer {resp.json()['token']}"}
