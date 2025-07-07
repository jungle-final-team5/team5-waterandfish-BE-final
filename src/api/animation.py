from datetime import datetime
import os
from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import FileResponse, JSONResponse
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from .utils import get_user_id_from_token, convert_objectid

router = APIRouter(prefix="/anim", tags=["animations"])

LESSON_TYPE = ["letter", "word", "sentence"]


@router.get("/{lesson_id}")
async def get_lesson_animation_by_id(
    lesson_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """특정 레슨의 애니메이션 조회(파일을 반환)"""
    try:
        obj_id = ObjectId(lesson_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid lesson ID"
        )
    
    lesson = await db.Lessons.find_one({"_id": obj_id})
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Lesson not found"
        )
    
    anim_filename = lesson.get("media_url", "default")
    file_path = f"public/animations/{anim_filename}"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animation file not found"
        )
    
    return FileResponse(
        path=file_path,
        filename=anim_filename,
        media_type="application/json"  # 파일 타입에 맞게 수정
    )

@router.get("/")
async def get_lesson_animation_by_word(
    word: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """특정 레슨의 애니메이션 조회 | 단어 기준으로 이루어짐"""
    """problem : 먹는 배, 타는 배, 사람 배 구분 불가"""
    try:
        obj_word = word
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid lesson ID"
        )
    
    lesson = await db.Lessons.find_one({"sign_text": obj_word})
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Lesson not found"
        )
    
    anim_filename = lesson.get("media_url", "default")
    file_path = f"public/animations/{anim_filename}"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animation file not found"
        )
    
    return FileResponse(
        path=file_path,
        filename=anim_filename,
        media_type="application/json"  # 파일 타입에 맞게 수정
    )
