from fastapi import APIRouter, Request, HTTPException, Depends, Cookie
from fastapi.responses import JSONResponse
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from datetime import datetime, timedelta
from jose import jwt, JWTError
from ..core.config import settings

router = APIRouter(prefix="/learning", tags=["learning"])

CHAPTER_TYPES = ["word", "sentence"]
LESSON_TYPE = ["letter", "word", "sentence"]

# ObjectId를 JSON에 맞게 문자열로 변환
def convert_objectid(doc):
    if isinstance(doc, list):
        return [convert_objectid(item) for item in doc]
    elif isinstance(doc, dict):
        new_doc = {}
        for key, value in doc.items():
            if key == "_id":
                new_doc["id"] = str(value)
            elif isinstance(value, ObjectId):
                new_doc[key] = str(value)
            else:
                new_doc[key] = convert_objectid(value)
        return new_doc
    return doc

@router.post("/category")
async def create_category(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    data = await request.json()
    if "name" not in data or "description" not in data or "order" not in data:
        raise HTTPException(status_code=400, detail="Missing 'name', 'description' or 'order'")
    
    categories = {
        "name": data["name"],
        "description": data["description"],
        "order": data["order"]
    }
    result = await db.Category.insert_one(categories)
    created = await db.Category.find_one({"_id": result.inserted_id})
    return JSONResponse(content=convert_objectid(created))

@router.post("/chapter")
async def create_chapter(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    data = await request.json()
    
    if "title" not in data or "description" not in data or "categoryname" not in data or "order" not in data or "type" not in data:
        raise HTTPException(status_code=400, detail="Missing required fields")
    if data["type"] not in CHAPTER_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {data['type']}")
    
    cate = await db.Category.find_one({"name": data["categoryname"]})
    if not cate:
        raise HTTPException(status_code=404, detail="category not found")
    
    chapters = {
        "title": data["title"],
        "description": data["description"],
        "type": data["type"],
        "category_id": cate["_id"],
        "order": data["order"]
    }
    result = await db.Chapters.insert_one(chapters)
    created = await db.Chapters.find_one({"_id": result.inserted_id})
    return JSONResponse(content=convert_objectid(created))

@router.post("/lesson")
async def create_lesson(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    data = await request.json()
    if "sign" not in data or "description" not in data or "type" not in data or "order" not in data or "chapter" not in data:
        raise HTTPException(status_code=400, detail="Missing required fields")
    if data["type"] not in LESSON_TYPE:
        raise HTTPException(status_code=400, detail=f"Invalid type: {data['type']}")
    
    chap = await db.Chapters.find_one({"title": data["chapter"]})
    if not chap:
        raise HTTPException(status_code=404, detail="chapter not found")
    
    lesson = {
        "sign_text": data["sign"],
        "description": data["description"],
        "content_type": data["type"],
        "order_index": data["order"],
        "chapter_id": chap["_id"],
        "media_url": data["url"],
        "model_data_url": None
    }
    result = await db.Lessons.insert_one(lesson)
    created = await db.Lessons.find_one({"_id": result.inserted_id})
    return JSONResponse(content=convert_objectid(created))

@router.get("/categories")
async def get_categories(db: AsyncIOMotorDatabase = Depends(get_db)):
    categories = await db.Category.find().to_list(length=None)
    
    results = []
    for c in categories:
        category_id = c["_id"]
        chapters = await db.Chapters.find({"category_id": category_id}).to_list(length=None)
        
        # 각 챕터의 signs 가져오기
        chapter_list = []
        for chapter in chapters:
            chapid = chapter["_id"]
            signs = await db.Lessons.find({"chapter_id": chapid}).to_list(length=None)
            
            # SignWord 형태로 변환
            sign_list = []
            for sign in signs:
                sign_list.append({
                    "id": str(sign["_id"]),
                    "word": sign.get("sign_text", ""),
                    "category": c["name"],
                    "difficulty": "medium",
                    "videoUrl": str(sign.get("media_url", "")),
                    "description": sign.get("description", "")
                })
            
            chapter_list.append({
                "id": str(chapter["_id"]),
                "title": chapter["title"],
                "type": chapter.get("type", None),
                "signs": sign_list,
                "categoryId": str(category_id),
                "order_index": chapter.get("order", chapter.get("order_index", 0))
            })
        
        results.append({
            "id": str(c["_id"]),
            "title": c["name"],
            "description": c["description"],
            "chapters": chapter_list,
            "icon": "📚",
            "order_index": c.get("order", c.get("order_index", 0))
        })
    return results

@router.get("/chapter/{category}")
async def get_chapters(category: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        obj_id = ObjectId(category)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid category ID")

    cate = await db.Category.find_one({"_id": obj_id})
    if not cate:
        raise HTTPException(status_code=404, detail="Category not found")

    chapters = await db.Chapters.find({"category_id": obj_id}).to_list(length=None)
    chapterresult = []
    for c in chapters:
        chapid = c["_id"]
        signs = await db.Lessons.find({"chapter_id": chapid}).to_list(length=None)
        
        # SignWord 형태로 변환
        sign_list = []
        for sign in signs:
            sign_list.append({
                "id": str(sign["_id"]),
                "word": sign.get("sign_text", ""),
                "category": cate["name"],
                "difficulty": "medium",
                "videoUrl": str(sign.get("media_url", "")),
                "description": sign.get("description", "")
            })
        
        chapterresult.append({
            "id": str(c["_id"]),
            "title": c["title"],
            "type": c.get("type", None),
            "signs": sign_list,
            "categoryId": str(obj_id),
            "order_index": c.get("order", c.get("order_index", 0))
        })

    result = {
        "id": str(cate["_id"]),
        "title": cate["name"],
        "description": cate["description"],
        "chapters": chapterresult,
        "icon": "📚",
        "order_index": cate.get("order", cate.get("order_index", 0))
    }

    return result

@router.get("/progress/failures-by-username/{username}")
async def get_failed_lessons_by_username(username: str,db: AsyncIOMotorDatabase = Depends(get_db)):
    # 1) username으로 user 찾기
    user = await db.users.find_one({"nickname": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = user["_id"]

    # 2) 해당 user_id로 실패한 progress 조회
    failed_progresses = await db.Progress.find({
        "user_id": user_id,
        "status": "fail"
    }).to_list(length=None)

    # 3) lesson_id 목록 추출
    lesson_ids = [p["lesson_id"] for p in failed_progresses]
    if not lesson_ids:
        return []

    # 4) lesson_id로 Lessons 조회
    lessons = await db.Lessons.find({
        "_id": {"$in": lesson_ids}
    }).to_list(length=None)

    # 5) 각 레슨에 category 이름과 word 필드 추가
    for lesson in lessons:
        # chapter 정보 가져오기
        chapter = await db.Chapters.find_one({"_id": lesson["chapter_id"]})
        category = await db.Category.find_one({"_id": chapter["category_id"]}) if chapter else None

        # category 이름 추가
        lesson["category"] = category["name"] if category else "Unknown"

        # word 필드에 sign을 복사
        lesson["word"] = lesson.get("sign_text", "")

    # 6) ObjectId 변환 및 반환
    return [convert_objectid(lesson) for lesson in lessons]

@router.get("/chapters/{chapter_id}")
async def get_chapter(chapter_id: str,db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        oid = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(status_code=400, detail="잘못된 챕터 ID입니다.")
    
    chapter = await db.Chapters.find_one({"_id": oid})
    if not chapter:
        raise HTTPException(status_code=404, detail="챕터를 찾을 수 없습니다.")
    
    title = chapter.get("title", "기타")
    return {"type": title}

# 기존 learning router는 그대로 두고, streak API만 별도 user_daily_activity_router로 분리
user_daily_activity_router = APIRouter(prefix="/user/daily-activity", tags=["user_daily_activity"])

@user_daily_activity_router.get("/streak")
async def get_streak(request: Request, db=Depends(get_db), access_token: str = Cookie(None)):
    # 1. user_id 추출
    token = access_token or request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="No access token provided")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="No user id in token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")

    # 2. 활동 날짜 리스트 조회
    activities = await db.user_daily_activity.find(
        {"user_id": ObjectId(user_id), "has_activity": True}
    ).sort("activity_date", 1).to_list(length=None)
    study_dates = [a["activity_date"].strftime("%Y-%m-%d") for a in activities]
    date_list = [a["activity_date"].date() for a in activities]

    # 3. streak 계산 함수 (가장 최근 날짜부터 연속 streak 계산)
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
        # current streak: 가장 최근 날짜부터 연속 streak 계산
        current_streak = 1 if dates else 0
        for i in range(len(dates)-1, 0, -1):
            if (dates[i] - dates[i-1]).days == 1:
                current_streak += 1
            else:
                break
        return current_streak, max_streak

    current_streak, longest_streak = calculate_streaks(date_list)

    return {
        "studyDates": study_dates,
        "currentStreak": current_streak,
        "longestStreak": longest_streak
    }

@user_daily_activity_router.post("/complete")
async def complete_today_activity(request: Request, db=Depends(get_db), access_token: str = Cookie(None)):
    # 1. user_id 추출
    token = access_token or request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="No access token provided")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="No user id in token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
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
    return {"message": "오늘 활동이 기록되었습니다."}