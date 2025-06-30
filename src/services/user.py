from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..models.user import User, UserCreate, UserUpdate, PyObjectId, UserORM
from datetime import datetime
from passlib.context import CryptContext
from bson import ObjectId
from fastapi import HTTPException
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB용 UserService (기존)
class UserService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    def _hash_password(self, password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)
    
    async def create_user(self, user: UserCreate) -> User:
        """사용자 생성"""
        # 이메일 중복 체크
        existing_user = await self.db.users.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")
        
        user_data = {
            "email": user.email,
            "password_hash": self._hash_password(user.password),
            "nickname": user.nickname,
            "handedness": user.handedness,
            "streak_days": 0,
            "overall_progress": 0,
            "description": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await self.db.users.insert_one(user_data)
        
        # 생성된 사용자 데이터 조회
        created_user = await self.db.users.find_one({"_id": result.inserted_id})
        if not created_user:
            raise HTTPException(status_code=500, detail="사용자 생성 후 조회 실패")
        
        return self._convert_to_user_model(created_user)
    
    async def get_all_users(self) -> List[User]:
        """전체 사용자 조회"""
        users = []
        cursor = self.db.users.find()
        async for user in cursor:
            users.append(self._convert_to_user_model(user))
        return users
    
    async def get_user_by_id(self, user_id: str) -> User:
        """ID로 사용자 조회"""
        try:
            object_id = ObjectId(user_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        user = await self.db.users.find_one({"_id": object_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return self._convert_to_user_model(user)
    
    async def update_user(self, user_id: str, user_update: UserUpdate) -> User:
        """사용자 정보 수정"""
        try:
            object_id = ObjectId(user_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        user = await self.db.users.find_one({"_id": object_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        update_data = user_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        await self.db.users.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )
        
        # 업데이트된 사용자 정보 조회
        updated_user = await self.db.users.find_one({"_id": object_id})
        if not updated_user:
            raise HTTPException(status_code=500, detail="업데이트된 사용자 조회 실패")
        
        return self._convert_to_user_model(updated_user)
    
    async def delete_user(self, user_id: str) -> bool:
        """사용자 삭제"""
        try:
            object_id = ObjectId(user_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        result = await self.db.users.delete_one({"_id": object_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return True
    
    def _convert_to_user_model(self, user_data: dict) -> User:
        """MongoDB 데이터를 User 모델로 변환"""
        return User(
            _id=user_data["_id"],
            email=user_data["email"],
            nickname=user_data["nickname"],
            handedness=user_data.get("handedness") or None,
            streak_days=user_data.get("streak_days", 0),
            overall_progress=user_data.get("overall_progress", 0),
            description=user_data.get("description"),
            created_at=user_data.get("created_at", datetime.utcnow()),
            updated_at=user_data.get("updated_at", datetime.utcnow())
        )

# SQLAlchemy용 UserService (새로 추가)
class UserServiceSQL:
    def __init__(self, db: Session):
        self.db = db
    
    def _hash_password(self, password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)
    
    def create_user(self, user_create: UserCreate) -> UserORM:
        """사용자 생성"""
        # 이메일 중복 체크
        if self.db.query(UserORM).filter(UserORM.email == user_create.email).first():
            raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")

        hashed_password = self._hash_password(user_create.password)
        db_user = UserORM(
            email=user_create.email,
            password_hash=hashed_password,
            nickname=user_create.nickname,
            handedness=user_create.handedness,
            streak_days=user_create.streak_days or 0,
            overall_progress=user_create.overall_progress or 0,
            description=user_create.description,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def get_all_users(self) -> List[UserORM]:
        """전체 사용자 조회"""
        return self.db.query(UserORM).all()
    
    def get_user_by_id(self, user_id: int) -> UserORM:
        """ID로 사용자 조회"""
        user = self.db.query(UserORM).filter(UserORM.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    
    def update_user(self, user_id: int, user_update: UserUpdate) -> UserORM:
        """사용자 정보 수정"""
        user = self.db.query(UserORM).filter(UserORM.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        # SQLAlchemy의 onupdate가 자동으로 처리하므로 수동 설정 불필요
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        user = self.db.query(UserORM).filter(UserORM.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        self.db.delete(user)
        self.db.commit()
        return True
