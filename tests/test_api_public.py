import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

import asyncio

@pytest.mark.asyncio
async def test_test_page():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/test")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "test_types" in data["data"]

@pytest.mark.asyncio
async def test_search_no_query():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/search")
    # 쿼리 파라미터 없으면 422 Unprocessable Entity
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_review_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/review")
    # 인증 없으면 401 또는 403
    assert response.status_code in (401, 403)

@pytest.mark.asyncio
async def test_lessons_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/lessons", json={})
    assert response.status_code in (400, 401, 403, 422)  # 400도 허용

@pytest.mark.asyncio
async def test_chapters_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/chapters", json={})
    assert response.status_code in (400, 401, 403, 422)

@pytest.mark.asyncio
async def test_progress_overview_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/progress/overview")
    assert response.status_code in (401, 403) 