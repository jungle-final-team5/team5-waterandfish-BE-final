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

@router.put("/password")
async def change_password(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user_id = get_current_user_id(request)
    data = await request.json()
    current_password = data.get("currentPassword")
    new_password = data.get("newPassword")
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="currentPassword와 newPassword가 필요합니다.")

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    stored_password = user.get("password_hash", "")
    # bcrypt 해시가 아니면 평문 비교
    verified = False
    try:
        verified = pwd_context.verify(current_password, stored_password)
    except Exception:
        # 해시가 아니면 평문 비교
        if current_password == stored_password:
            verified = True
    if not verified:
        raise HTTPException(status_code=400, detail="기존 비밀번호가 일치하지 않습니다.")

    hashed_password = pwd_context.hash(new_password)
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": hashed_password}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="비밀번호 변경에 실패했습니다.")
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

