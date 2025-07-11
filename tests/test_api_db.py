import os
from dotenv import load_dotenv
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
from motor.motor_asyncio import AsyncIOMotorClient
from src.db.session import get_db

load_dotenv()  # .env 파일 자동 로드

TEST_MONGO_URI = os.getenv("TEST_MONGO_URI")
TEST_DB_NAME = os.getenv("TEST_DB_NAME")

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop()
    yield loop

@pytest_asyncio.fixture(scope="function")
async def test_db():
    client = AsyncIOMotorClient(TEST_MONGO_URI)
    db = client[TEST_DB_NAME]
    # 테스트 전 users 컬렉션 초기화
    await db.users.delete_many({})
    yield db
    # 테스트 후 정리
    await client.drop_database(TEST_DB_NAME)
    client.close()

@pytest.fixture(scope="function")
def override_get_db(test_db):
    async def _override():
        yield test_db
    return _override

@pytest.mark.asyncio
async def test_create_and_get_user(test_db, override_get_db):
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 테스트용 유저 데이터 삽입
        user_doc = {
            "email": "testuser@example.com",
            "nickname": "테스트유저",
            "handedness": "R",
            "streak_days": 0,
            "overall_progress": 0,
            "description": "",
            "created_at": "2025-07-11T10:37:11.501+00:00",
            "updated_at": "2025-07-11T10:37:47.024+00:00"
        }
        await test_db.users.insert_one(user_doc)
        # 실제 API 호출 (예: /user/me)
        response = await ac.get("/user/me")
        assert response.status_code == 401  # 인증 없으므로 401
    app.dependency_overrides = {} 