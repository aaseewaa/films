"""Интеграционные тесты health-эндпоинтов (httpx, без внешней сети)."""
import pytest


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_health_returns_ok(api_client):
    response = await api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "app" in body


@pytest.mark.asyncio
async def test_root_lists_endpoints(api_client):
    response = await api_client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["docs"] == "/docs"
    assert "search" in body["endpoints"]


@pytest.mark.db
@pytest.mark.asyncio
async def test_health_db_when_postgres_available(api_client):
    """Требует живой PostgreSQL из `.env` (DATABASE_URL)."""
    response = await api_client.get("/health/db")
    if response.status_code != 200:
        pytest.skip(f"БД недоступна: {response.status_code} {response.text}")
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "connected"
