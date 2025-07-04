from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import user_router
from .api.auth import router as auth_router
from .api.learning import router as learning_router
from .api.learning import user_daily_activity_router  # streak API 라우터 추가
from .api.badge import router as badge_router
from .api.search import router as search_router
from .core.config import settings

app = FastAPI(title="WaterAndFish API", version="1.0.0")

# CORS 미들웨어 추가 - 더 안전한 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # 설정된 origins만 허용
    allow_credentials=True,  # 쿠키 포함 요청 허용
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # 허용할 HTTP 메서드
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "X-CSRFToken",
        "Cookie",
    ],  # 허용할 헤더
    expose_headers=["Set-Cookie"],  # 클라이언트가 접근 가능한 헤더
    max_age=600,  # preflight 요청 캐시 시간 (초)
)

@app.get("/")
def read_root():
    return {"message": "Hello, team5-waterandfish-BE!", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "cors_origins": settings.cors_origins_list}

# 기존 경로 유지 (하위 호환성)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(learning_router)
app.include_router(badge_router)
app.include_router(search_router)
app.include_router(user_daily_activity_router)  # streak API 라우터 등록

# API prefix 추가 (새로운 경로)
app.include_router(user_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(learning_router, prefix="/api")
app.include_router(badge_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(user_daily_activity_router, prefix="/api")  # streak API 라우터 등록 
