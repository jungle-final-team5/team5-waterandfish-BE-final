# src/api/search.py
from fastapi import APIRouter, Query, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..services.embedding import embed
from ..db.session import get_db
from bson import ObjectId

router = APIRouter(prefix="/search", tags=["search"])

def projection():
    return {
        "lesson_id": {"$toString": "$_id"},
        "sign_text": 1,
        "score": {"$meta": "vectorSearchScore"}
    }

POST_FILTER = {
    "$and": [
        {"content_type": {"$ne": "letter"}},      # letter 제외
        {"sign_text":   {"$type": "string"}},     # 문자열만
        {"sign_text":   {"$regex": "[^0-9]"}}     # 숫자-only 제외
    ]
}

def convert_objectid_to_str(doc):
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc

@router.get("")
async def semantic_search(
    q: str = Query(..., min_length=1),
    k: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    lessons_col = db.Lessons
    q_vec = embed(q)

    pipe = [
        {
            "$vectorSearch": {
                "index":         "waterandfish_lessons",
                "path":          "embedding",
                "queryVector":   q_vec,
                "limit":         k,
                "numCandidates": k * 5
            }
        },
        { "$match": POST_FILTER },
        { "$project": projection() }
    ]

    hits = await lessons_col.aggregate(pipe).to_list(k)

    # fallback: prefix 검색
    if not hits:
        prefix_cond = {**POST_FILTER, "sign_text": {"$regex": f"^{q}"}}
        fallback_hits = await lessons_col.find(prefix_cond, {"_id": 1, "sign_text": 1}).limit(k).to_list(length=k)
        # ObjectId를 문자열로 변환 + score 필드 추가
        hits = [
            {
                "lesson_id": str(doc["_id"]),
                "sign_text": doc["sign_text"],
                "score": None
            }
            for doc in fallback_hits
        ]

    # 모든 hits에 대해 ObjectId를 str로 변환 (lesson_id 외 다른 필드도 포함)
    hits = [convert_objectid_to_str(hit) for hit in hits]

    if not hits:
        raise HTTPException(status_code=404, detail="No results")

    return {
        "success": True,
        "data": hits,
        "message": "검색 결과"
    }
