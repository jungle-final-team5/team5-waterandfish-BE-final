from pydantic_settings import BaseSettings
from typing import List
from pydantic import Field
import os

class Settings(BaseSettings):
    # CORS 설정 (쉼표로 구분된 문자열)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    root_path: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 프론트엔드 URL 설정 (배포 환경용)
    FRONTEND_URL: str = "http://localhost:5173"

    # JWT 설정
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Google OAuth2 설정
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # Kakao OAuth2 설정
    KAKAO_CLIENT_ID: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = ""

    # MongoDB 설정
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "waterandfish"
    
    # AWS S3 설정
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-northeast-2"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        if isinstance(self.CORS_ORIGINS, str):
            origins = []
            # 대괄호 제거하고 쉼표로 분리
            cors_str = self.CORS_ORIGINS.strip("[]").replace('"', '').replace("'", "")
            for origin in cors_str.split(","):
                origin = origin.strip()
                if origin:  # 빈 문자열 제외
                    origins.append(origin)
            return origins
        return self.CORS_ORIGINS if isinstance(self.CORS_ORIGINS, list) else [self.CORS_ORIGINS]

settings = Settings()