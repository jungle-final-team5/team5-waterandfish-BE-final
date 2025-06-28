from fastapi import APIRouter, HTTPException, Depends
from typing import List
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..models.user import User, UserCreate, UserUpdate
from ..db.session import get_db
from ..services.user import UserService

router = APIRouter(prefix="/user", tags=["users"])

def get_user_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> UserService:
    """사용자 서비스 의존성 주입"""
    return UserService(db)

# 회원가입: POST /user/signup
@router.post("/signup", response_model=User)
async def create_user(
    user: UserCreate, 
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.create_user(user)

# 전체 유저 조회: GET /user/
@router.get("/", response_model=List[User])
async def list_users(user_service: UserService = Depends(get_user_service)):
    return await user_service.get_all_users()

# 특정 유저 조회: GET /user/{user_id}
@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str, 
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.get_user_by_id(user_id)

# 특정 유저 수정: PUT /user/{user_id}
@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str, 
    user_update: UserUpdate, 
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.update_user(user_id, user_update)

# 특정 유저 삭제: DELETE /user/{user_id}
@router.delete("/{user_id}")
async def delete_user(
    user_id: str, 
    user_service: UserService = Depends(get_user_service)
):
    await user_service.delete_user(user_id)
    return {"ok": True}