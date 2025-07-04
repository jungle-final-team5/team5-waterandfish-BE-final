# routes/search.py
from fastapi import APIRouter, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from ..services.embedding import embed
from ..core.config import settings

router = APIRouter(prefix="/search", tags=["search"])

MONGO = AsyncIOMotorClient(settings.MONGODB_URL)
COL   = MONGO["waterandfish"]["Lessons"]   # sign_text, embedding, lesson_id …

def projection():
    return {
        "_id": 0,
        "sign_text": 1,
        "lesson_id": 1,
        "score": {"$meta": "vectorSearchScore"}
    }

@router.get("")
async def semantic_search(q: str = Query(..., min_length=1), k: int = 10):
    """벡터→없으면 prefix→그래도 없으면 404"""
    q_vec = embed(q)
    pipe = [
        {   # ① letter 제외
            "$match": { "content_type": { "$ne": "letter" } }
        },
        {"$vectorSearch": {
            "index": "waterandfish_lessons",
            "path": "embedding",
            "queryVector": q_vec,
            "limit": k,
            "numCandidates": k * 5
        }},
        {"$project": projection()}
    ]
    hits = await COL.aggregate(pipe).to_list(k)
    if not hits:
        # fallback: sign_text startsWith q
        hits = await COL.find(
            {"sign_text": {"$regex": f"^{q}"}},
            projection()
        ).limit(k).to_list(length=k)
    if not hits:
        raise HTTPException(status_code=404, detail="No results")
    return hits
