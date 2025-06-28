from odmantic import AIOEngine
from motor.motor_asyncio import AsyncIOMotorClient

import os
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGODB_URL)
engine = AIOEngine(motor_client=client, database="waterandfish")

async def get_engine():
    yield engine 
        