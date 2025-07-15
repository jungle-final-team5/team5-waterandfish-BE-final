from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from src.services.s3_utils import s3_utils
import json
import os

router = APIRouter()

BUCKET = "waterandfish-s3"  # 실제 버킷명으로 수정 필요

@router.post("/upload-sign-video")
async def upload_sign_video(
    label: str = Form(...),
    video: UploadFile = File(...)
):
    try:
        video_url, label_url = s3_utils.upload_video_and_label(label, video)
        return JSONResponse({"video_url": video_url, "label_url": label_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 