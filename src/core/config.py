from pydantic_settings import BaseSettings
from typing import List
from pydantic import Field
import os

class Settings(BaseSettings):
    # CORS 설정 (쉼표로 구분된 문자열 → List 자동 변환됨)
    CORS_ORIGINS: List[str] = Field(default_factory=list)


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()