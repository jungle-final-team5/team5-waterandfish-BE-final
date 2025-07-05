from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import user_router
from .api.auth import router as auth_router
from .api.learning import router as learning_router
from .api.learning import user_daily_activity_router  # streak API 라우터 추가
from .api.badge import router as badge_router
from .api.search import router as search_router
from .core.config import settings

app = FastAPI()

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # 리스트로 넘겨야 함!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello, team5-waterandfish-BE!"}

# 기존 경로 유지 (하위 호환성)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(learning_router)
app.include_router(badge_router)
app.include_router(search_router)
app.include_router(user_daily_activity_router)  # streak API 라우터 등록

