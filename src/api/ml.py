from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from ..services.ml_service import deploy_model
from .utils import get_user_id_from_token, require_auth, convert_objectid

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/deploy/{chapter_id}")
async def deploy_chapter_model(
    chapter_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    use_webrtc: bool = False
):
    use_webrtc = False
    print("deploy_chapter_model")   
    """챕터에 해당하는 모델 서버를 배포하고 WebSocket URL 목록 반환"""
    user_id = require_auth(request)
    
    try:
        chapter_obj_id = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid chapter ID"
        )
    
    # 챕터 존재 확인
    chapter = await db.Chapters.find_one({"_id": chapter_obj_id})
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chapter not found"
        )
    
    try:
        # 모델 서버 배포
        ws_urls = await deploy_model(chapter_obj_id, db, use_webrtc)
        print('ws_urls', ws_urls)
        if not ws_urls:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "data": {"ws_urls": []},
                    "message": "해당 챕터에 배포할 모델이 없습니다"
                }
            )
        
        server_type = "WebRTC" if use_webrtc else "WebSocket"
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {"ws_urls": ws_urls, "server_type": server_type},
                "message": f"{server_type} 모델 서버 배포 완료: {len(ws_urls)}개"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"모델 서버 배포 실패: {str(e)}"
        )


@router.get("/status/{chapter_id}")
async def get_chapter_model_status(
    chapter_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """챕터 모델 서버 상태 확인"""
    user_id = get_user_id_from_token(request)
    
    try:
        chapter_obj_id = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid chapter ID"
        )
    
    # 챕터 존재 확인
    chapter = await db.Chapters.find_one({"_id": chapter_obj_id})
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chapter not found"
        )
    
    try:
        # TODO: 모델 서버 상태 확인 로직 구현
        # model_server_manager에서 상태 확인 메서드 필요
        
        return {
            "success": True,
            "data": {
                "chapter_id": chapter_id,
                "status": "unknown",  # TODO: 실제 상태로 변경
                "servers": []  # TODO: 실제 서버 정보로 변경
            },
            "message": "모델 서버 상태 조회 완료"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"모델 서버 상태 조회 실패: {str(e)}"
        )


@router.delete("/stop/{chapter_id}")
async def stop_chapter_model(
    chapter_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """챕터 모델 서버 중지"""
    user_id = require_auth(request)
    
    try:
        chapter_obj_id = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid chapter ID"
        )
    
    # 챕터 존재 확인
    chapter = await db.Chapters.find_one({"_id": chapter_obj_id})
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chapter not found"
        )
    
    try:
        # TODO: 모델 서버 중지 로직 구현
        # model_server_manager에서 서버 중지 메서드 필요
        
        return {
            "success": True,
            "data": {"chapter_id": chapter_id},
            "message": "모델 서버 중지 완료"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"모델 서버 중지 실패: {str(e)}"
        )


@router.get("/health")
async def get_ml_service_health(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """ML 서비스 전체 상태 확인"""
    user_id = get_user_id_from_token(request)
    
    try:
        # TODO: 전체 ML 서비스 상태 확인 로직 구현
        # - 활성 모델 서버 수
        # - 서버 리소스 사용률
        # - 에러 발생 현황 등
        
        return {
            "success": True,
            "data": {
                "status": "healthy",  # TODO: 실제 상태로 변경
                "active_servers": 0,  # TODO: 실제 활성 서버 수로 변경
                "total_memory_usage": "0MB",  # TODO: 실제 메모리 사용량으로 변경
                "uptime": "0h 0m",  # TODO: 실제 업타임으로 변경
                "last_check": datetime.utcnow().isoformat()
            },
            "message": "ML 서비스 상태 조회 완료"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML 서비스 상태 조회 실패: {str(e)}"
        )

