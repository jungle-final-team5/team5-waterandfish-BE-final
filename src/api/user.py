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

@router.delete("/delete-account")
async def delete_account(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    data: dict = Body(...)
):
    password = data.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="비밀번호가 필요합니다.")
    
    # 쿠키에서 토큰 추출 (auth.py와 일관성 유지)
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="인증 정보가 없습니다.")
    
    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    
    # user_id를 ObjectId로 변환
    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id 형식이 올바르지 않습니다.")
    
    user = await db.users.find_one({"_id": object_id})
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not pwd_context.verify(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")
    
    result = await db.users.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="계정 삭제에 실패했습니다.")
    
    # 성공 응답과 함께 쿠키 삭제
    response = JSONResponse(content={"message": "계정이 성공적으로 삭제되었습니다."})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response