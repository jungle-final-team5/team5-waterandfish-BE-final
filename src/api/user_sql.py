from fastapi import APIRouter, Request, HTTPException, Depends, status
from typing import List
from sqlalchemy.orm import Session
from ..models.user import User, UserCreate, UserUpdate, UserORM
from ..db.sqlalchemy_session import get_sqlalchemy_db
from ..services.user import UserServiceSQL
from .utils import require_auth

router = APIRouter(prefix="/user-sql", tags=["users-sql"])

def get_user_service_sql(db: Session = Depends(get_sqlalchemy_db)) -> UserServiceSQL:
    """SQLAlchemy 사용자 서비스 의존성 주입"""
    return UserServiceSQL(db)

def validate_user_access(request_user_id: int, target_user_id: int):
    """사용자 접근 권한 검증"""
    if request_user_id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

# 회원가입: POST /user-sql/signup
@router.post("/signup")
def create_user(
    user: UserCreate, 
    user_service: UserServiceSQL = Depends(get_user_service_sql)
):
    """회원가입"""
    try:
        created_user = user_service.create_user(user)
        return {
            "success": True,
            "data": created_user,
            "message": "회원가입 성공"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# 전체 유저 조회: GET /user-sql/
@router.get("/")
def list_users(
    request: Request,
    user_service: UserServiceSQL = Depends(get_user_service_sql)
):
    """전체 유저 조회 (관리자 전용)"""
    # TODO: 관리자 권한 검증 추가 필요
    require_auth(request)
    
    try:
        users = user_service.get_all_users()
        return {
            "success": True,
            "data": users,
            "message": "전체 유저 조회 성공"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )

# 특정 유저 조회: GET /user-sql/{user_id}
@router.get("/{user_id}")
def get_user(
    user_id: int,
    request: Request,
    user_service: UserServiceSQL = Depends(get_user_service_sql)
):
    """특정 유저 조회"""
    request_user_id = require_auth(request)
    validate_user_access(request_user_id, user_id)
    
    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "success": True,
            "data": user,
            "message": "유저 조회 성공"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user"
        )

# 특정 유저 수정: PUT /user-sql/{user_id}
@router.put("/{user_id}")
def update_user(
    user_id: int,
    user_update: UserUpdate,
    request: Request,
    user_service: UserServiceSQL = Depends(get_user_service_sql)
):
    """특정 유저 수정"""
    request_user_id = require_auth(request)
    validate_user_access(request_user_id, user_id)
    
    try:
        updated_user = user_service.update_user(user_id, user_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "success": True,
            "data": updated_user,
            "message": "유저 정보 수정 성공"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )

# 특정 유저 삭제: DELETE /user-sql/{user_id}
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    user_service: UserServiceSQL = Depends(get_user_service_sql)
):
    """특정 유저 삭제"""
    request_user_id = require_auth(request)
    validate_user_access(request_user_id, user_id)
    
    try:
        user_service.delete_user(user_id)
        return {
            "success": True,
            "message": "유저 삭제 성공"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        ) 