from motor.motor_asyncio import AsyncIOMotorClient
from typing import AsyncGenerator

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "waterandfish"

client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]

async def get_db() -> AsyncGenerator[AsyncIOMotorClient, None]:
    try:
        yield database
    finally:
        pass  # Motor client는 애플리케이션 종료 시 자동으로 연결을 닫습니다 