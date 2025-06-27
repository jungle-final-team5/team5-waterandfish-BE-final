from pydantic import BaseModel
from typing import Optional
from enum import Enum
import datetime
from sqlalchemy import Column, Integer, String, Enum as SAEnum, DateTime, SmallInteger
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class Handedness(str, Enum):
    L = 'L'
    R = 'R'
    I = 'I'

class UserBase(BaseModel):
    email: str
    nickname: str
    handedness: Handedness
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
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True

class HandednessEnum(str, enum.Enum):
    L = "L"
    R = "R"
    I = "I"

class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=False)
    handedness = Column(SAEnum(HandednessEnum), nullable=False)
    streak_days = Column(SmallInteger, default=0)
    overall_progress = Column(SmallInteger, default=0)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow) 