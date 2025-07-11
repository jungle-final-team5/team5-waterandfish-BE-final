from fastapi import APIRouter, HTTPException, Depends, Request, Body
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
from bson import ObjectId


router = APIRouter(prefix="/auth", tags=["auth"])

# JWT 설정 - settings에서 가져오기
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
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    nickname: str

@router.get("/auth-test")
async def auth_test():
    return {"message": "auth router is working!"}

async def ensure_today_activity(user_id, db):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    record = await db.user_daily_activity.find_one({
        "user_id": ObjectId(user_id),
        "activity_date": today
    })
    if not record:
        await db.user_daily_activity.insert_one({
            "user_id": ObjectId(user_id),
            "activity_date": today,
            "has_activity": False,
        })
# 로그인: POST /auth/signin
@router.post("/signin")
async def signin(login_data: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다.")
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다.")
    # 로그인 성공 시 오늘 출석 레코드 생성
    await ensure_today_activity(user["_id"], db)
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
        # 출석 레코드 생성
        await ensure_today_activity(user["_id"], db)
        # refresh_token 생성
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user["_id"], "email": user["email"]},
            expires_delta=refresh_token_expires
        )
        response = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?user_id={user['_id']}&email={user['email']}&nickname={user['nickname']}&handedness={user.get('handedness','')}&streak_days={user.get('streak_days',0)}&overall_progress={user.get('overall_progress',0)}&description={user.get('description','')}")
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
        # 출석 레코드 생성
        await ensure_today_activity(user["_id"], db)
        # refresh_token 생성
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user["_id"], "email": user["email"]},
            expires_delta=refresh_token_expires
        )
        response = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?user_id={user['_id']}&email={user['email']}&nickname={user['nickname']}&handedness={user.get('handedness','')}&streak_days={user.get('streak_days',0)}&overall_progress={user.get('overall_progress',0)}&description={user.get('description','')}")
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
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        email = payload.get("email")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # 새 토큰 생성
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
    
    # 응답 생성
    response = JSONResponse(content={"message": "Token refreshed"})
    
    # 쿠키 설정
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
    
    return response

@router.post("/logout")
async def logout():
    response = JSONResponse(content={"message": "로그아웃 성공"})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response

@router.delete("/delete-account")
async def delete_account(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    data: dict = Body(...)
):
    email = data.get("email")
    
    if not email:
        raise HTTPException(status_code=400, detail="이메일이 필요합니다.")
    
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="인증 정보가 없습니다.")
    
    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_email = payload.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    
    # user_id를 ObjectId로 변환
    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id 형식이 올바르지 않습니다.")
    
    # DB에서 유저 조회
    user = await db.users.find_one({"_id": object_id})
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 입력된 이메일과 토큰의 이메일이 일치하는지 확인
    if user["email"] != email:
        raise HTTPException(status_code=401, detail="이메일이 일치하지 않습니다.")
    
    # 토큰의 이메일과도 일치하는지 추가 검증
    if token_email and token_email != email:
        raise HTTPException(status_code=401, detail="토큰의 이메일과 일치하지 않습니다.")
    
    # 유저 삭제
    result = await db.users.delete_one({"_id": object_id})
    # 관련 progress 및 활동 데이터도 모두 삭제
    await db.users_badge.delete_many({"user_id": object_id})
    await db.user_daily_activity.delete_many({"user_id": object_id})
    await db.User_Lesson_Progress.delete_many({"user_id": object_id})
    await db.User_Chapter_Progress.delete_many({"user_id": object_id})
    await db.User_Category_Progress.delete_many({"user_id": object_id})
    await db.Progress.delete_many({"user_id": object_id})
    
    response = JSONResponse(content={"message": "계정이 성공적으로 삭제되었습니다."})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response

# 회원가입: POST /auth/signup
@router.post("/signup")
async def signup(signup_data: SignupRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    # 이메일 중복 확인
    existing_user = await db.users.find_one({"email": signup_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")
    
    # 비밀번호 해시화
    hashed_password = pwd_context.hash(signup_data.password)
    
    # 새 사용자 생성
    new_user = {
        "email": signup_data.email,
        "password_hash": hashed_password,
        "nickname": signup_data.nickname,
        "handedness": "",
        "streak_days": 0,
        "overall_progress": 0,
        "description": "",
        "created_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(new_user)
    new_user["_id"] = str(result.inserted_id)
    
    # 토큰 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": str(result.inserted_id), "email": new_user["email"]}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(result.inserted_id), "email": new_user["email"]},
        expires_delta=refresh_token_expires
    )
    
    # 응답 생성
    user_dict = {
        "_id": str(result.inserted_id),
        "email": new_user["email"],
        "nickname": new_user["nickname"],
        "handedness": new_user["handedness"],
        "streak_days": new_user["streak_days"],
        "overall_progress": new_user["overall_progress"],
        "description": new_user["description"]
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