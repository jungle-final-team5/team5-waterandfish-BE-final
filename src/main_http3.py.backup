from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from .api import user_router
from .api.auth import router as auth_router
from .api.learning import router as learning_router
from .api.categories import router as categories_router
from .api.chapters import router as chapters_router
from .api.lessons import router as lessons_router
from .api.progress import router as progress_router
from .api.study import router as study_router
from .api.attendance import router as attendance_router
from .api.users import router as users_router
from .api.learn import router as learn_router
from .api.quiz import router as quiz_router
from .api.test import router as test_router
from .api.review import router as review_router
from .api.badge import router as badge_router
from .api.search import router as search_router
from .api.ml import router as ml_router
from .api.animation import router as anim_router
from .api.recommendations import router as recommendations_router
from .api.video_upload import router as video_upload_router
from .core.config import settings
from .services.embedding import _get_model

app = FastAPI(
    title="Water and Fish API",
    description="수어 학습 플랫폼 API - HTTP/3 지원",
    version="1.0.0"
)

# 신뢰할 수 있는 호스트 미들웨어 추가
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["waterandfish.shop", "*.waterandfish.shop", "localhost", "127.0.0.1"]
)

# CORS 미들웨어 추가 - HTTP/3 지원을 위한 헤더 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
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
        "Alt-Svc",  # HTTP/3 지원을 위한 헤더
        "Upgrade-Insecure-Requests",
    ],
    expose_headers=["Set-Cookie", "Alt-Svc"],
    max_age=600,
)

# HTTP/3 지원을 위한 미들웨어
@app.middleware("http")
async def add_http3_headers(request: Request, call_next):
    response = await call_next(request)
    
    # HTTP/3 Alt-Svc 헤더 추가
    response.headers["Alt-Svc"] = 'h3=":443"; ma=86400'
    
    # 보안 헤더 추가
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # HTTP/3 지원 브라우저를 위한 최적화
    if "h3" in request.headers.get("accept-encoding", ""):
        response.headers["Vary"] = "Accept-Encoding"
    
    return response

@app.get("/")
def read_root():
    return {
        "message": "Hello, team5-waterandfish-BE!", 
        "status": "healthy",
        "http3_supported": True,
        "domain": "waterandfish.shop"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "cors_origins": settings.cors_origins_list,
        "http3_enabled": True
    }

# HTTP/3 연결 테스트 엔드포인트
@app.get("/http3-test")
def http3_test(request: Request):
    return {
        "protocol": request.url.scheme,
        "headers": dict(request.headers),
        "http3_supported": True,
        "alt_svc": 'h3=":443"; ma=86400'
    }

# 프론트엔드 라우트에 맞춘 새로운 API 라우터들
app.include_router(categories_router)  # /category
app.include_router(learn_router)       # /learn
app.include_router(quiz_router)        # /quiz
app.include_router(test_router)        # /test
app.include_router(review_router)      # /review
app.include_router(anim_router)        # /anim
app.include_router(video_upload_router) # /video_upload

# 기존 RESTful API 라우터들 (하위 호환성)
app.include_router(chapters_router)
app.include_router(lessons_router)
app.include_router(progress_router)
app.include_router(study_router)
app.include_router(attendance_router)
app.include_router(users_router)

# 기존 라우터들 (하위 호환성)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(learning_router)  # deprecated
app.include_router(badge_router)
app.include_router(search_router)
app.include_router(ml_router)
app.include_router(recommendations_router)

@app.on_event("startup")
async def preload_embedding_model():
    # 임베딩 모델을 미리 메모리에 로딩
    _get_model()
    print("🚀 HTTP/3 지원 서버가 시작되었습니다!")
    print("🌐 도메인: waterandfish.shop")
    print("🔒 HTTPS/HTTP3 지원 활성화")
