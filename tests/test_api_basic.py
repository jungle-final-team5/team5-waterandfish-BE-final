import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

import asyncio

@pytest.mark.asyncio
async def test_auth_test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/auth/auth-test")
    assert response.status_code == 200
    assert response.json() == {"message": "auth router is working!"}

@pytest.mark.asyncio
async def test_category_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/category/list")
    # 200 OK, success 필드가 True인지 확인
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "message" in data 