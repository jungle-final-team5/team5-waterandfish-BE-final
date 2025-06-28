from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from ..models.user import User
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import jwt
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

# JWT 설정
SECRET_KEY = "your-secret-key-here"  # 실제 운영에서는 환경변수로 관리
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

class LoginRequest(BaseModel):
    email: str
    password: str

@router.get("/auth-test")
async def auth_test():
    return {"message": "auth router is working!"}

# 로그인: POST /auth/signin
@router.post("/signin")
async def signin(login_data: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    # 사용자 조회
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다.")
    
    # 비밀번호 검증
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다.")
    
    # JWT 토큰 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "email": user["email"]}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "_id": str(user["_id"]),
            "email": user["email"],
            "nickname": user["nickname"],
            "handedness": user.get("handedness"),
            "streak_days": user.get("streak_days", 0),
            "overall_progress": user.get("overall_progress", 0),
            "description": user.get("description")
        }
    }