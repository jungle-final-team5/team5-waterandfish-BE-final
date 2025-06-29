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
from fastapi.responses import RedirectResponse, Response, JSONResponse


router = APIRouter(prefix="/auth", tags=["auth"])

# JWT 설정
SECRET_KEY = "your-secret-key-here"  # 실제 운영에서는 환경변수로 관리
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

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

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
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
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다.")
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다.")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "email": user["email"]}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user["_id"]), "email": user["email"]},
        expires_delta=refresh_token_expires
    )
    user_dict = {
        "_id": str(user["_id"]),
        "email": user["email"],
        "nickname": user["nickname"],
        "handedness": user.get("handedness", ""),
        "streak_days": user.get("streak_days", 0),
        "overall_progress": user.get("overall_progress", 0),
        "description": user.get("description", "")
    }
    response = JSONResponse(content={"user": user_dict})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS*24*60*60
    )
    return response

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
        access_token = result["access_token"]
        user = result["user"]
        # refresh_token 생성
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user["_id"], "email": user["email"]},
            expires_delta=refresh_token_expires
        )
        response = RedirectResponse(url=f"http://localhost:5173/auth/callback?user_id={user['_id']}&email={user['email']}&nickname={user['nickname']}&handedness={user.get('handedness','')}&streak_days={user.get('streak_days',0)}&overall_progress={user.get('overall_progress',0)}&description={user.get('description','')}")
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS*24*60*60
        )
        return response
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
        access_token = result["access_token"]
        user = result["user"]
        # refresh_token 생성
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user["_id"], "email": user["email"]},
            expires_delta=refresh_token_expires
        )
        response = RedirectResponse(url=f"http://localhost:5173/auth/callback?user_id={user['_id']}&email={user['email']}&nickname={user['nickname']}&handedness={user.get('handedness','')}&streak_days={user.get('streak_days',0)}&overall_progress={user.get('overall_progress',0)}&description={user.get('description','')}")
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS*24*60*60
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Kakao 로그인 실패: {str(e)}")

@router.post("/refresh")
async def refresh_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        email = payload.get("email")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_access_token = create_access_token(
        data={"sub": user_id, "email": email},
        expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user_id, "email": email},
        expires_delta=refresh_token_expires
    )
    response = Response()
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS*24*60*60
    )
    response.media_type = "application/json"
    response.body = b'{"message": "Token refreshed"}'
    return response

@router.post("/logout")
async def logout():
    response = JSONResponse(content={"message": "로그아웃 성공"})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response