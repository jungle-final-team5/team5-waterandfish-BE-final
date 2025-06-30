from pydantic_settings import BaseSettings
from typing import List
from pydantic import Field
import os

class Settings(BaseSettings):
    # CORS 설정 (쉼표로 구분된 문자열 → List 자동 변환됨)
    CORS_ORIGINS: str = "http://localhost:5173"
    
    # JWT 설정
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Google OAuth2 설정
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # Kakao OAuth2 설정
    KAKAO_CLIENT_ID: str
    KAKAO_CLIENT_SECRET: str
    KAKAO_REDIRECT_URI: str

    # MongoDB 설정
    MONGODB_URL: str
    DATABASE_NAME: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
