from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from ..models.user import User, UserCreate, UserUpdate, UserORM
from ..db.sqlalchemy_session import get_sqlalchemy_db
from ..services.user import UserServiceSQL

router = APIRouter(prefix="/user-sql", tags=["users-sql"])

def get_user_service_sql(db: Session = Depends(get_sqlalchemy_db)) -> UserServiceSQL:
    """SQLAlchemy 사용자 서비스 의존성 주입"""
    return UserServiceSQL(db)

# 회원가입: POST /user-sql/signup
@router.post("/signup", response_model=UserORM)
def create_user(
    user: UserCreate, 
    user_service: UserServiceSQL = Depends(get_user_service_sql)
):
    return user_service.create_user(user)

# 전체 유저 조회: GET /user-sql/
@router.get("/", response_model=List[UserORM])
def list_users(user_service: UserServiceSQL = Depends(get_user_service_sql)):
    return user_service.get_all_users()

# 특정 유저 조회: GET /user-sql/{user_id}
@router.get("/{user_id}", response_model=UserORM)
def get_user(
    user_id: int, 
    user_service: UserServiceSQL = Depends(get_user_service_sql)
):
    return user_service.get_user_by_id(user_id)

# 특정 유저 수정: PUT /user-sql/{user_id}
@router.put("/{user_id}", response_model=UserORM)
def update_user(
    user_id: int, 
    user_update: UserUpdate, 
    user_service: UserServiceSQL = Depends(get_user_service_sql)
):
    return user_service.update_user(user_id, user_update)

# 특정 유저 삭제: DELETE /user-sql/{user_id}
@router.delete("/{user_id}")
def delete_user(
    user_id: int, 
    user_service: UserServiceSQL = Depends(get_user_service_sql)
):
    user_service.delete_user(user_id)
    return {"ok": True} 