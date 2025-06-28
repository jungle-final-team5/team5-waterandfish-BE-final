import httpx
from typing import Optional, Dict, Any
from ..core.config import settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
import jwt

class SocialAuthService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    async def get_or_create_user(self, email: str, nickname: str, social_id: str, provider: str) -> Dict[str, Any]:
        """소셜 로그인 사용자를 조회하거나 생성"""
        # 기존 사용자 조회
        user = await self.db.users.find_one({"email": email})
        
        if user:
            # 기존 사용자가 있으면 소셜 정보 업데이트
            await self.db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        f"{provider}_id": social_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return user
        
        # 새 사용자 생성
        user_data = {
            "email": email,
            "nickname": nickname,
            f"{provider}_id": social_id,
            "handedness": None,
            "streak_days": 0,
            "overall_progress": 0,
            "description": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await self.db.users.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        return user_data
    
    async def google_oauth(self, code: str) -> Dict[str, Any]:
        """Google OAuth2.0 처리"""
        async with httpx.AsyncClient() as client:
            # 1. 액세스 토큰 요청
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI
            }
            
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            token_info = token_response.json()
            
            # 2. 사용자 정보 요청
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {token_info['access_token']}"}
            user_response = await client.get(user_info_url, headers=headers)
            user_response.raise_for_status()
            user_info = user_response.json()
            
            # 3. 사용자 생성 또는 조회
            user = await self.get_or_create_user(
                email=user_info["email"],
                nickname=user_info.get("name", user_info["email"].split("@")[0]),
                social_id=user_info["id"],
                provider="google"
            )
            
            # 4. JWT 토큰 생성
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = self.create_access_token(
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
    
    async def kakao_oauth(self, code: str) -> Dict[str, Any]:
        """Kakao OAuth2.0 처리"""
        async with httpx.AsyncClient() as client:
            # 1. 액세스 토큰 요청
            token_url = "https://kauth.kakao.com/oauth/token"
            token_data = {
                "grant_type": "authorization_code",
                "client_id": settings.KAKAO_CLIENT_ID,
                "client_secret": settings.KAKAO_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.KAKAO_REDIRECT_URI
            }
            
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            token_info = token_response.json()
            
            # 2. 사용자 정보 요청
            user_info_url = "https://kapi.kakao.com/v2/user/me"
            headers = {"Authorization": f"Bearer {token_info['access_token']}"}
            user_response = await client.get(user_info_url, headers=headers)
            user_response.raise_for_status()
            user_info = user_response.json()
            
            # 3. 사용자 생성 또는 조회
            kakao_account = user_info.get("kakao_account", {})
            profile = kakao_account.get("profile", {})
            
            user = await self.get_or_create_user(
                email=kakao_account.get("email", f"kakao_{user_info['id']}@kakao.com"),
                nickname=profile.get("nickname", f"카카오사용자_{user_info['id']}"),
                social_id=str(user_info["id"]),
                provider="kakao"
            )
            
            # 4. JWT 토큰 생성
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = self.create_access_token(
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