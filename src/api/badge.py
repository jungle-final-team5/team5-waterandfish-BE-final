from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from ..models.badge import Badge, UserBadge, BadgeWithStatus
import jwt
from ..core.config import settings
from bson import ObjectId
from typing import List
import datetime

router = APIRouter(prefix="/badge", tags=["badges"])

def get_current_user_id(request: Request) -> str:
    # Authorization 헤더 또는 쿠키에서 토큰 추출
    auth_header = request.headers.get("authorization")
    token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="No token found")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="No user id in token")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/", response_model=List[BadgeWithStatus])
async def get_badges_with_status(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """전체 배지 목록 + 현재 사용자의 달성 상태 조회"""
    
    # Badge 테이블에서 모든 데이터 가져오기
    all_badges = await db.Badge.find().to_list(length=None)

    own_badges = await db.users_badge.find().to_list(length=None)
    
    # BadgeWithStatus 형태로 변환
    result = []
    for badge in all_badges:
        result.append(BadgeWithStatus(
            id=badge["id"],
            code=badge["code"],
            name=badge["name"],
            description=badge["description"],
            icon_url=badge["icon_url"],
            is_earned=False  # 기본값
        ))
    
    return result

@router.get("/earned", response_model=List[BadgeWithStatus])
async def get_earned_badges(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """현재 사용자가 획득한 배지만 조회"""
    
    # 현재 사용자 ObjectId 획득
    user_id_str = get_current_user_id(request)
    user_object_id = ObjectId(user_id_str)
    
    # 사용자가 획득한 배지 조회 (JOIN 형태)
    pipeline = [
        {"$match": {"userid": user_object_id}},
        {"$lookup": {
            "from": "badge",
            "localField": "badge_id",
            "foreignField": "id",
            "as": "badge_info"
        }},
        {"$unwind": "$badge_info"}
    ]
    
    earned_badges = await db.users_badge.aggregate(pipeline).to_list(length=None)
    
    result = []
    for item in earned_badges:
        badge = item["badge_info"]
        result.append(BadgeWithStatus(
            id=badge["id"],
            code=badge["code"],
            name=badge["name"],
            description=badge["description"],
            icon_url=badge["icon_url"],
            is_earned=True,
            userid=str(item["userid"]),
            link=item["link"],
            acquire=item["acquire"]
        ))
    
    return result

@router.post("/earn/{badge_id}")
async def earn_badge(
    badge_id: int,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """배지 획득 (트리거 발생 시 호출)"""
    
    # 현재 사용자 email 획득
    try:
        payload = jwt.decode(request.cookies.get("access_token"), settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        current_user_email = payload.get("email")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 배지 존재 확인
    badge = await db.badge.find_one({"id": badge_id})
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    
    # 이미 획득했는지 확인
    existing = await db.users_badge.find_one({
        "userid": current_user_email,
        "badge_id": badge_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Badge already earned")
    
    # 배지 획득 기록
    user_badge = {
        "badge_id": badge_id,
        "userid": current_user_email,
        "link": "earned",  # 기본값
        "acquire": datetime.datetime.utcnow()
    }
    
    result = await db.users_badge.insert_one(user_badge)
    
    return {
        "message": f"Badge '{badge['name']}' earned successfully!",
        "badge_id": badge_id,
        "acquire": user_badge["acquire"]
    }