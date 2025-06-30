from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import AsyncGenerator
from ..core.config import settings

MONGODB_URL = settings.MONGODB_URL
DATABASE_NAME = settings.DATABASE_NAME

client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]

async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    try:
        yield database
    finally:
        pass