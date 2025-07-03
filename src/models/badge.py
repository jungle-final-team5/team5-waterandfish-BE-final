from pydantic import BaseModel, Field
from typing import Optional, List
import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return handler(ObjectId)

# Badge 기본 정보 (전체 배지 목록)
class Badge(BaseModel):
    id: int
    code: str
    name: str
    description: str
    icon_url: str

# 사용자가 획득한 배지 (users_badge 컬렉션)
class UserBadge(BaseModel):
    badge_id: int
    userid: str
    link: str
    acquire: datetime.datetime

# API 응답용 (배지 + 달성 여부)
class BadgeWithStatus(BaseModel):
    id: int
    code: str
    name: str
    description: str
    icon_url: str

class OwnBadge(BaseModel):
    id: int
    userid: str
    link: str
    acquire: str
    