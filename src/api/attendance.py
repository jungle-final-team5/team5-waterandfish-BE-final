from datetime import datetime, time
from fastapi import APIRouter, Request, HTTPException, Depends, status, Cookie
from fastapi.responses import JSONResponse
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from .utils import get_user_id_from_token, require_auth


router = APIRouter(prefix="/attendance", tags=["attendance"])


def get_utc_today():
    now_utc = datetime.utcnow()
    return datetime.combine(now_utc.date(), time(0, 0, 0))


@router.get("/streak")
async def get_streak(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    access_token: str = Cookie(None)
):
    """출석 스트릭 조회"""
    user_id = require_auth(request, access_token)
    
    # 활동 날짜 리스트 조회
    activities = await db.user_daily_activity.find(
        {"user_id": ObjectId(user_id), "has_activity": True}
    ).sort("activity_date", 1).to_list(length=None)
    
    # UTC 기준으로 날짜 변환
    study_dates = [a["activity_date"].strftime("%Y-%m-%d") for a in activities]
    date_list = [a["activity_date"].date() for a in activities]
    
    # streak 계산 함수 (가장 최근 날짜부터 연속 streak 계산)
    def calculate_streaks(dates):
        if not dates:
            return 0, 0
        
        # longest streak
        max_streak = 1
        temp_streak = 1
        prev = dates[0]
        
        for i in range(1, len(dates)):
            if (dates[i] - prev).days == 1:
                temp_streak += 1
            else:
                temp_streak = 1
            if temp_streak > max_streak:
                max_streak = temp_streak
            prev = dates[i]
        
        # current streak: 오늘(UTC)부터 연속된 날짜만 카운트
        from datetime import datetime as dt_datetime
        today_utc = dt_datetime.utcnow().date()
        if dates and dates[-1] == today_utc:
            current_streak = 1
            for i in range(len(dates)-1, 0, -1):
                if (dates[i] - dates[i-1]).days == 1:
                    current_streak += 1
                else:
                    break
        else:
            current_streak = 0
        
        return current_streak, max_streak
    
    current_streak, longest_streak = calculate_streaks(date_list)
    
    return {
        "success": True,
        "data": {
            "studyDates": study_dates,
            "currentStreak": current_streak,
            "longestStreak": longest_streak
        },
        "message": "출석 스트릭 조회 성공"
    }

@router.post("/complete")
async def complete_today_activity(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    access_token: str = Cookie(None)
):
    """오늘 출석 완료"""
    user_id = require_auth(request, access_token)
    
    today = get_utc_today()
    
    result = await db.user_daily_activity.update_one(
        {"user_id": ObjectId(user_id), "activity_date": today},
        {
            "$set": {
                "has_activity": True,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        # 오늘 출석 레코드가 없으면 새로 생성
        await db.user_daily_activity.insert_one({
            "user_id": ObjectId(user_id),
            "activity_date": today,
            "has_activity": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    return {
        "success": True,
        "message": "오늘 활동이 기록되었습니다."
    } 