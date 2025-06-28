from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import user_router
from .api.auth import router as auth_router
from .core.config import settings

app = FastAPI()

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello, team5-waterandfish-BE!"}

app.include_router(user_router)
app.include_router(auth_router) 