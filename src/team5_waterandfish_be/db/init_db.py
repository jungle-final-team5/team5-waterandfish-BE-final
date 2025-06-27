import asyncio
from team5_waterandfish_be.db.session import engine
from team5_waterandfish_be.models.user import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("DB 테이블 생성 완료!")

if __name__ == "__main__":
    asyncio.run(init_db()) 