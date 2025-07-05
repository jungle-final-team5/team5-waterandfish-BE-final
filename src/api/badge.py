from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from ..models.badge import Badge, SimpleInput, UserBadge, BadgeWithStatus
import jwt
from ..core.config import settings
from bson import ObjectId
from bson.timestamp import Timestamp
from typing import List, Dict
import datetime
import json

router = APIRouter(prefix="/badge", tags=["badges"])

def convert_timestamp(obj):
    """MongoDB Timestamp를 datetime으로 변환"""
    if isinstance(obj, Timestamp):
        return datetime.datetime.fromtimestamp(obj.time)
    return obj

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

# StatsService 기능 통합
async def collect_user_stats(db: AsyncIOMotorDatabase, user_id: ObjectId) -> Dict:
    """사용자 통계 수집"""
    stats = {}
    
    # 학습 진도 통계
    progress_count = await db.User_Lesson_Progress.count_documents({ "user_id": user_id, "status": {"$ne": "not_started"}})
    stats["total_words"] = progress_count
    chapter_count = await db.User_Chapter_Progress.count_documents({ "user_id": user_id, "complete": {"$ne": "false"}})
    stats["total_chapter"] = chapter_count
    
    # 연속 학습일 통계
    user_activity = await db.user_daily_activity.find_one({"user_id": user_id})
    stats["streak_days"] = user_activity.get("current_streak", 0) if user_activity else 0
    
    # 사용자 기본 정보
    user = await db.users.find_one({"_id": user_id})
    if user:
        
        days_since_created = 0
        created_at = user.get("created_at")
        if created_at:
            today = datetime.datetime.now()
            if isinstance(created_at, datetime.datetime):
                days_since_created = (today - created_at).days
            else:
            # created_at이 문자열인 경우 datetime으로 변환
                try:
                    created_date = datetime.datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                    days_since_created = (today - created_date).days
                except:
                    days_since_created = 0
        else:
            days_since_created = 0
        stats["start_at"] = days_since_created
    
    return stats

async def check_badge_condition(badge: Dict, user_stats: Dict) -> bool:
    """배지 획득 조건 확인"""
    try:
        badge_code = badge.get("code")
        badge_cond = badge.get("rule_json", {}).get("value")
        
        start_at = user_stats.get("start_at")
        total_words = user_stats.get("total_words")
        total_chapter = user_stats.get("total_chapter")
        streak_days = user_stats.get("streak_days")

        if badge_code == "day_streak_3":
            return streak_days >= badge_cond
        elif badge_code == "day_streak_7":
            return streak_days >= badge_cond
        elif badge_code == "day_streak_14":
            return streak_days >= badge_cond
        
        elif badge_code == "done_word_1":
            return total_words >= badge_cond
        elif badge_code == "done_word_20":
            return total_words >= badge_cond
        elif badge_code == "done_word_40":
            return total_words >= badge_cond
        
        elif badge_code == "done_chapter_3":
            return total_chapter >= badge_cond
        elif badge_code == "done_chapter_6":
            return total_chapter >= badge_cond
        elif badge_code == "done_chapter_12":
            return total_chapter >= badge_cond
        
        elif badge_code == "id_created_7d":
            return start_at >= badge_cond
        elif badge_code == "id_created_14d":
            return start_at >= badge_cond
        elif badge_code == "id_created_28d":
            return start_at >= badge_cond
        
        # elif badge_code == "epic_1":
        #     return start_at >= badge_cond
        # elif badge_code == "epic_2":
        #     return start_at >= badge_cond
        # elif badge_code == "epic_3":
        #     return start_at >= badge_cond
        
        return False
    except (json.JSONDecodeError, KeyError):
        return False

def calculate_progress_percentage(badge: Dict, user_stats: Dict) -> int:
    """배지 획득 진행률 계산"""
    try:
        rule_json = json.loads(badge.get("rule_json", "{}"))
        event = rule_json.get("event")

        if event == "first_lesson":
            return min(100, (user_stats.get("completed_lessons", 0) / 1) * 100)
        elif event == "ten_lessons":
            return min(100, (user_stats.get("completed_lessons", 0) / 10) * 100)
        elif event == "goal_streak":
            required_days = rule_json.get("days", 30)
            return min(100, (user_stats.get("streak_days", 0) / required_days) * 100)
        elif event == "progress_milestone":
            required_progress = rule_json.get("progress", 50)
            return min(100, (user_stats.get("overall_progress", 0) / required_progress) * 100)
        
        return 0
    except (json.JSONDecodeError, KeyError):
        return 0

@router.get("/")
async def get_badges_with_status(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """전체 배지 목록 + 현재 사용자의 달성 상태 조회"""
    
    try:
        user_id_str = get_current_user_id(request)
        user_object_id = ObjectId(user_id_str)
        
        # 사용자가 획득한 배지 조회
        earned_badges = await db.users_badge.find({"userid": user_object_id}).to_list(length=None)
        earned_badge_ids = {badge["badge_id"]: badge for badge in earned_badges}
    except:
        # 로그인하지 않은 경우
        earned_badge_ids = {}
    
    # 전체 배지 목록 조회
    all_badges = await db.Badge.find().to_list(length=None)
    
    result = []
    for badge in all_badges:
        badge_id = badge["id"]
        earned_badge = earned_badge_ids.get(badge_id)
        is_earned = earned_badge is not None
        
        result.append({
            "id": badge_id,
            "code": badge["code"],
            "name": badge["name"],
            "description": badge["description"],
            "icon_url": badge["icon_url"],
            "is_earned": is_earned,
            "acquire": convert_timestamp(earned_badge["acquire"]) if earned_badge else None
        })
    
    return result

@router.get("/earned")
async def get_earned_badges(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """현재 사용자가 획득한 배지만 조회"""
    
    user_id_str = get_current_user_id(request)
    user_object_id = ObjectId(user_id_str)
    
    # users_badge 컬렉션에서 해당 사용자의 배지 조회
    user_badges = await db.users_badge.find({"userid": str(user_object_id)}).to_list(length=None)
    
    # ObjectId를 문자열로 변환하여 반환
    result = []
    for badge in user_badges:
        result.append({
            "_id": str(badge["_id"]),
            "badge_id": badge["badge_id"],
            "userid": str(badge["userid"]),
            "link": badge["link"],
            "acquire": convert_timestamp(badge["acquire"])
        })
    
    return result

@router.get("/all-earned")
async def get_all_earned_badges(
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """모든 users_badge 데이터 조건 없이 가져오기"""
    
    # users_badge 컬렉션에서 모든 데이터 조회
    all_user_badges = await db.users_badge.find().to_list(length=None)
    
    # ObjectId와 Timestamp를 문자열로 변환하여 반환
    result = []
    for badge in all_user_badges:
        result.append({
            "_id": str(badge["_id"]),
            "badge_id": badge["badge_id"],
            "userid": str(badge["userid"]),
            "link": badge["link"],
            "acquire": convert_timestamp(badge["acquire"])
        })
    
    return result

@router.post("/check-badges")
async def check_and_award_badges(
    input_data: SimpleInput,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user_id_str = get_current_user_id(request)
    user_object_id = ObjectId(user_id_str)
   

    # TODO : 여기서 받은 인자에 따라 값을 업데이트를 시킨다.
        # 왜 주석? : 현재 수행 갯수에 대한 내용이 users 단일 레코드가 아니라 users_**_** 컬렉션들로 구성되어 있음. 
        # 분명 리팩토리 대상이고, 해당 내용 리팩토링 시 아래 코드가 사용 될 것으로 기대..

    # if input_data.input_str == "day":
    #     # 최초 출석 시 호출됨. 기존에 호출된적 없는지에 대한 안전 장치 없음
    #     current_streak = user_data.get("streak_days", 0)
    #     new_streak = current_streak + 1
    #     await db.users.update_one({"_id": user_object_id}, {"$set": {"streak_days": new_streak}})
    # elif input_data.input_str == "word":
    #     # 단어 수행 시 호출
    # elif input_data.input_str == "chapter":
    #     # 챕터 수행 시 호출 됨. 기존에 수행한 챕터가 아니어야합니다.
    # elif input_data.input_str == "account":
    #     pass
    # else:
    #     pass

    user_stats = await collect_user_stats(db, user_object_id)
    """사용자 활동을 확인하고 새로운 배지 획득 처리"""

    # 모든 배지 규칙 조회
    all_badges = await db.Badge.find().to_list(length=None)
    
    # 이미 획득한 배지 조회
    earned_badges = await db.users_badge.find({"userid": str(user_object_id)}).to_list(length=None)
    earned_badge_ids = {badge["badge_id"] for badge in earned_badges}
    # 사용자 통계 수집
    
    # 각 배지 조건 확인 및 획득 처리
    newly_awarded = []
    for badge in all_badges:
        badge_id = badge["id"]
        
        # 이미 획득한 배지는 건너뛰기
        if badge_id in earned_badge_ids:
            continue
        
        # 배지 조건 확인
        if await check_badge_condition(badge, user_stats):
            # 배지 획득 처리
            user_badge = {
                "badge_id": badge_id,
                "userid": str(user_object_id),
                "link": "earned",
                "acquire": datetime.datetime.now()
            }
            await db.users_badge.insert_one(user_badge)
            
            newly_awarded.append({
                "badge_id": badge_id,
                "name": badge["name"],
                "description": badge["description"]
            })
    
    return {
        "message": f"{len(newly_awarded)} badges awarded",
        "newly_awarded_badges": newly_awarded
    }

@router.get("/progress")
async def get_badge_progress(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """사용자의 배지 획득 진행 상황 조회"""
    user_id_str = get_current_user_id(request)
    user_object_id = ObjectId(user_id_str)
    
    # 사용자 통계 수집
    user_stats = await collect_user_stats(db, user_object_id)
    
    # 모든 배지와 진행 상황
    all_badges = await db.Badge.find().to_list(length=None)
    earned_badges = await db.users_badge.find({"userid": user_object_id}).to_list(length=None)
    earned_badge_ids = {badge["badge_id"]: badge for badge in earned_badges}
    
    badge_progress = []
    for badge in all_badges:
        badge_id = badge["id"]
        earned_badge = earned_badge_ids.get(badge_id)
        is_earned = earned_badge is not None
        
        # 진행률 계산
        progress_percentage = 100 if is_earned else calculate_progress_percentage(badge, user_stats)
        
        badge_progress.append({
            "badge_id": badge_id,
            "code": badge["code"],
            "name": badge["name"],
            "description": badge["description"],
            "icon_url": badge["icon_url"],
            "is_earned": is_earned,
            "progress_percentage": progress_percentage,
            "acquire": convert_timestamp(earned_badge["acquire"]) if earned_badge else None
        })
    
    return {
        "user_stats": user_stats,
        "badge_progress": badge_progress
    }