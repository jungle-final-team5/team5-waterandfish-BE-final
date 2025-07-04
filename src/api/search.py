# src/api/search.py
from fastapi import APIRouter, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from services.embedding import embed
from ..core.config import settings

router = APIRouter(prefix="/search", tags=["search"])
COL = AsyncIOMotorClient(settings.MONGODB_URL)["waterandfish"]["Lessons"]

def projection():
    return {
        "_id": 0,
        "sign_text": 1,
        "lesson_id": 1,
        "score": {"$meta": "vectorSearchScore"}
    }

POST_FILTER = {
    "$and": [
        {"content_type": {"$ne": "letter"}},      # letter 제외
        {"sign_text":   {"$type": "string"}},     # 문자열만
        {"sign_text":   {"$regex": "[^0-9]"}}     # 숫자-only 제외
    ]
}

@router.get("")
async def semantic_search(q: str = Query(..., min_length=1), k: int = 10):
    q_vec = embed(q)

    pipe = [
        {   # ① vectorSearch – filter 없이 첫 스테이지
            "$vectorSearch": {
                "index":         "waterandfish_lessons",
                "path":          "embedding",
                "queryVector":   q_vec,
                "limit":         k,
                "numCandidates": k * 5
            }
        },
        { "$match": POST_FILTER },                # ② 숫자/letter 제거
        { "$project": projection() }              # ③ 필드 정리
    ]

    hits = await COL.aggregate(pipe).to_list(k)

    # ───── fallback: prefix 검색 ─────
    if not hits:
        prefix_cond = {**POST_FILTER,
                       "sign_text": {"$regex": f"^{q}"}}
        hits = await COL.find(prefix_cond,
                              projection())\
                        .limit(k).to_list(length=k)

    if not hits:
        raise HTTPException(status_code=404, detail="No results")

    return hits
