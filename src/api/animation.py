from datetime import datetime
import json
import os
from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import FileResponse, JSONResponse, Response
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
import boto3
import io

router = APIRouter(prefix="/anim", tags=["anim"])

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
    # print("[animation] lesson", lesson)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Lesson not found"
        )
    
    anim_filename = lesson.get("media_url", "default")
    print("[animation] anim_filename", anim_filename)
    
    # S3에서 파일 다운로드
    try:
        s3_client = boto3.client('s3')
        bucket_name = 'waterandfish-s3'
        key = f'animations/{anim_filename}'
        
        # S3에서 파일 객체 가져오기
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        file_content = response['Body'].read()
        
        # 파일 내용을 Response로 반환
        return Response(
            content=file_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={anim_filename}",
                "Cache-Control": "public, max-age=3600"  # 1시간 캐시
            }
        )
        
    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animation file not found in S3"
        )
    except Exception as e:
        print(f"[animation] S3 error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving animation file from S3"
        )