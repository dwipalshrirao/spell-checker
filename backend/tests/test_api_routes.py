import json

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app"] == "GrammarCheck"


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "model" in data


@pytest.mark.asyncio
async def test_ready(client):
    resp = await client.get("/ready")
    assert resp.status_code in (200, 503)


@pytest.mark.asyncio
async def test_check_invalid_input(client):
    resp = await client.post("/check", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_check_empty_text(client):
    resp = await client.post("/check", json={"text": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_check_too_long(client):
    resp = await client.post("/check", json={"text": "x" * 6000})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_feedback_invalid(client):
    resp = await client.post("/feedback", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_metrics(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data
