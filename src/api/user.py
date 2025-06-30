from fastapi import APIRouter, Depends, HTTPException, Request, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from ..services.user import UserService
from ..models.user import User
import jwt
from ..core.config import settings  # 환경설정에서 SECRET_KEY, ALGORITHM 불러오기
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from bson import ObjectId

router = APIRouter(prefix="/user", tags=["users"])

def get_user_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> UserService:
    return UserService(db)

def get_current_user_id(request: Request) -> str:
    # Authorization 헤더에서 토큰 추출
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No authorization header")
    token = auth_header.split(" ")[1]
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
    user_id = get_current_user_id(request)
    return await user_service.get_user_by_id(user_id)