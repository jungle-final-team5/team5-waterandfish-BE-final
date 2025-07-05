from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, status
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from .utils import get_user_id_from_token, require_auth, convert_objectid

router = APIRouter(prefix="/users", tags=["users"])


def validate_object_id(id_str: str, field_name: str = "ID"):
    """ObjectId 유효성 검증"""
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid {field_name}"
        )


def validate_user_access(request_user_id: str, target_user_id: str):
    """사용자 접근 권한 검증"""
    if request_user_id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


# 사용자 진도 조회 (전체 진도 데이터 - 고유 기능)
@router.get("/{user_id}/progress")
async def get_user_progress(
    user_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """사용자의 전체 진도 조회 - 모든 progress 데이터를 한번에 조회"""
    request_user_id = require_auth(request)
    validate_user_access(request_user_id, user_id)
    
    user_obj_id = validate_object_id(user_id, "user ID")
    
    lesson_progress = await db.User_Lesson_Progress.find({"user_id": user_obj_id}).to_list(length=None)
    chapter_progress = await db.User_Chapter_Progress.find({"user_id": user_obj_id}).to_list(length=None)
    category_progress = await db.User_Category_Progress.find({"user_id": user_obj_id}).to_list(length=None)
    
    return {
        "success": True,
        "data": {
            "lesson_progress": convert_objectid(lesson_progress),
            "chapter_progress": convert_objectid(chapter_progress),
            "category_progress": convert_objectid(category_progress)
        },
        "message": "유저 진도 조회 성공"
    }


 