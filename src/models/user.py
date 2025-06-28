from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from enum import Enum
import datetime
from bson import ObjectId
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Handedness(str, Enum):
    L = 'L'
    R = 'R'
    I = 'I'

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return handler(ObjectId)

# SQLAlchemy ORM 모델
class UserORM(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nickname = Column(String, nullable=False)
    handedness = Column(SQLEnum(Handedness), nullable=True)
    streak_days = Column(Integer, default=0)
    overall_progress = Column(Integer, default=0)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# Pydantic 모델들
class UserBase(BaseModel):
    email: str
    nickname: str
    handedness: Optional[Handedness] = None
    streak_days: Optional[int] = 0
    overall_progress: Optional[int] = 0
    description: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    handedness: Optional[Handedness] = None
    description: Optional[str] = None

class User(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
