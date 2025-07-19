from fastapi import APIRouter, Depends
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("/popular-by-search")
async def get_popular_signs_by_search(
    limit: int = 12,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """조회수(views)가 많은 단어(수어) 기준 인기 수어 12개 반환"""
    lessons = await db.Lessons.find({"content_type": {"$ne": "letter"}}).sort("views", -1).limit(limit).to_list(length=limit)
    for lesson in lessons:
        lesson["views"] = lesson.get("views", 0)
    result = [
        {
            "id": str(lesson["_id"]),
            "word": lesson.get("sign_text", ""),
            "description": lesson.get("description", ""),
            "videoUrl": lesson.get("media_url", ""),
            "views": lesson["views"]
        }
        for lesson in lessons
    ]
    return {
        "success": True,
        "data": result,
        "message": "조회수 기준 인기 수어 조회 성공"
    } 
