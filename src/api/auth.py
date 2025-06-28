from fastapi import APIRouter, HTTPException, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from ..models.user import User
from ..services.social_auth import SocialAuthService
from ..core.config import settings
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import jwt
from pydantic import BaseModel
from fastapi.responses import RedirectResponse


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

# Google OAuth2.0 시작
@router.get("/google")
async def google_auth_start():
    """Google OAuth2.0 인증 시작"""
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={settings.GOOGLE_REDIRECT_URI}&scope=openid%20email%20profile"
    # JSON 응답 대신 직접 리다이렉트
    return RedirectResponse(url=auth_url)

# Google OAuth2.0 콜백
@router.get("/google/callback")
async def google_auth_callback(code: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Google OAuth2.0 콜백 처리"""
    try:
        social_auth = SocialAuthService(db)
        result = await social_auth.google_oauth(code)
        
        # JSON 응답 대신 직접 프론트엔드로 리다이렉트
        frontend_url = f"http://localhost:5173/auth/callback?access_token={result['access_token']}&token_type={result['token_type']}"
        return RedirectResponse(url=frontend_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google 로그인 실패: {str(e)}")

# Kakao OAuth2.0 시작
@router.get("/kakao")
async def kakao_auth_start():
    """Kakao OAuth2.0 인증 시작"""
    auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={settings.KAKAO_CLIENT_ID}&redirect_uri={settings.KAKAO_REDIRECT_URI}&response_type=code"
    # JSON 응답 대신 직접 리다이렉트
    return RedirectResponse(url=auth_url)

# Kakao OAuth2.0 콜백
@router.get("/kakao/callback")
async def kakao_auth_callback(code: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Kakao OAuth2.0 콜백 처리"""
    try:
        social_auth = SocialAuthService(db)
        result = await social_auth.kakao_oauth(code)
        
        # JSON 응답 대신 직접 프론트엔드로 리다이렉트
        frontend_url = f"http://localhost:5173/auth/callback?access_token={result['access_token']}&token_type={result['token_type']}"
        return RedirectResponse(url=frontend_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Kakao 로그인 실패: {str(e)}")