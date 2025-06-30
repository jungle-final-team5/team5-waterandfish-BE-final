from fastapi import APIRouter, Depends, HTTPException, Request, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from ..services.user import UserService
from ..models.user import User, UserUpdate
import jwt
from ..core.config import settings  # 환경설정에서 SECRET_KEY, ALGORITHM 불러오기
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from bson import ObjectId
#김세현 바보

router = APIRouter(prefix="/user", tags=["users"])

def get_user_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> UserService:
    return UserService(db)

def get_current_user_id(request: Request) -> str:
    # 먼저 Authorization 헤더 확인
    auth_header = request.headers.get("authorization")
    token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        # Authorization 헤더가 없으면 쿠키에서 확인
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="No token found")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="No user id in token")
        return user_id
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/me", response_model=User)
async def get_me(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):

    # 쿠키에서 access_token 추출
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="인증 정보가 없습니다.")
    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="No user id in token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return await user_service.get_user_by_id(user_id)

@router.put("/me", response_model=User)
async def update_me(
    request: Request,
    user_update: UserUpdate,
    user_service: UserService = Depends(get_user_service)
):
    user_id = get_current_user_id(request)
    return await user_service.update_user(user_id, user_update)

