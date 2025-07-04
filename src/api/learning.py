from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, applications, Cookie
from fastapi.responses import JSONResponse
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
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
async def get_categories(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id = None
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
        except JWTError:
            pass
    categories = await db.Category.find().to_list(length=None)
    results = []
    for c in categories:
        category_id = c["_id"]
        chapters = await db.Chapters.find({"category_id": category_id}).to_list(length=None)
        chapter_list = []
        for chapter in chapters:
            chapid = chapter["_id"]
            signs = await db.Lessons.find({"chapter_id": chapid}).to_list(length=None)
            lesson_ids = [sign["_id"] for sign in signs]
            lesson_status_map = {}
            if user_id and lesson_ids:
                progresses = await db.User_Lesson_Progress.find({
                    "user_id": ObjectId(user_id),
                    "lesson_id": {"$in": lesson_ids}
                }).to_list(length=None)
                for p in progresses:
                    lesson_status_map[str(p["lesson_id"])] = p.get("status", "not_started")
            sign_list = []
            for sign in signs:
                sign_list.append({
                    "id": str(sign["_id"]),
                    "word": sign.get("sign_text", ""),
                    "category": c["name"],
                    "difficulty": "medium",
                    "videoUrl": str(sign.get("media_url", "")),
                    "description": sign.get("description", ""),
                    "status": lesson_status_map.get(str(sign["_id"]), "not_started")
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
            "emoji": c.get("emoji", "📚"),
            "order_index": c.get("order", c.get("order_index", 0))
        })
    return results

@router.get("/chapter/{category}")
async def get_chapters(category: str, request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id = None
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
        except JWTError:
            pass
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
        lesson_ids = [sign["_id"] for sign in signs]
        lesson_status_map = {}
        if user_id and lesson_ids:
            progresses = await db.User_Lesson_Progress.find({
                "user_id": ObjectId(user_id),
                "lesson_id": {"$in": lesson_ids}
            }).to_list(length=None)
            for p in progresses:
                lesson_status_map[str(p["lesson_id"])] = p.get("status", "not_started")
        sign_list = []
        for sign in signs:
            sign_list.append({
                "id": str(sign["_id"]),
                "word": sign.get("sign_text", ""),
                "category": cate["name"],
                "difficulty": "medium",
                "videoUrl": str(sign.get("media_url", "")),
                "description": sign.get("description", ""),
                "status": lesson_status_map.get(str(sign["_id"]), "not_started")
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

# 프로그레스 관련
# 카테고리 프로그레스 생성
@router.post("/progress/category/set")
async def progresscategoryset(request: Request,db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")  # 쿠키 이름 확인 필요
    data = await request.json()
    categoryid = ObjectId(data.get("categoryid"))
    if not token:
        raise HTTPException(status_code=401, detail="Token not found")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token decode failed or expired")
    category_progress = await db.User_Category_Progress.find_one({
        "user_id": ObjectId(user_id),
        "category_id": categoryid
    })

    if category_progress:
        # 이미 존재하면 아무 작업도 하지 않음
        return JSONResponse(status_code=200, content={"message": "Already initialized"})
        # 없으면 새로 생성
    await db.User_Category_Progress.insert_one({
        "user_id": ObjectId(user_id),
        "category_id": categoryid,
        "complete": False,
        "complete_at": None
    })
    return JSONResponse(status_code=201, content={"message": "Progress initialized"})
#챕터 프로그레스 및 레슨 프로그레스 생성
@router.post("/progress/chapter/set")
async def progressset(request: Request,db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")  # 쿠키 이름 확인 필요
    data = await request.json()
    chapid = ObjectId(data.get("chapid"))
    if not token:
        raise HTTPException(status_code=401, detail="Token not found")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token decode failed or expired")
    chapter_progress = await db.User_Chapter_Progress.find_one({
        "user_id": ObjectId(user_id),
        "chapter_id": chapid
    })

    if chapter_progress:
        return JSONResponse(status_code=200, content={"message": "Already initialized"})
        # 이미 존재하면 아무 작업도 하지 않음
        # 없으면 새로 생성
    await db.User_Chapter_Progress.insert_one({
        "user_id": ObjectId(user_id),
        "chapter_id": chapid,
        "complete": False,
        "complete_at": None
    })
    lessons = await db.Lessons.find({"chapter_id": chapid}).to_list(length=None)
    progress_bulk = [{
        "user_id": ObjectId(user_id),
        "lesson_id": lesson["_id"],
        "status": "not_started",
        "updated_at": datetime.utcnow()
    } for lesson in lessons]

    if progress_bulk:
        await db.User_Lesson_Progress.insert_many(progress_bulk)
    return JSONResponse(status_code=201, content={"message": "Progress initialized"})
#프로그레스 study
@router.post("/study/letter")
async def letterstudy(request: Request,db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")  # 쿠키 이름 확인 필요
    data = await request.json()
    if not token:
        raise HTTPException(status_code=401, detail="Token not found")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token decode failed or expired")
    cletters = data.get("checked", [])
    if not cletters:
        raise HTTPException(status_code=400, detail="학습한 글자가 없습니다")
    if(cletters[0] == "ㄱ"):
        chapter_doc = await db.Chapters.find_one({"title": "자음"})
        if not chapter_doc:
            raise HTTPException(status_code=404, detail="자음 챕터를 찾을 수 없습니다")
        chapid = chapter_doc["_id"]
    elif(cletters[0] == "ㅏ"):
        chapter_doc = await db.Chapters.find_one({"title": "모음"})
        if not chapter_doc:
            raise HTTPException(status_code=404, detail="모음 챕터를 찾을 수 없습니다")
        chapid = chapter_doc["_id"]
    letters = await db.Lessons.find({"chapter_id": chapid}).to_list(length=None)
    letter_ids = [lesson["_id"] for lesson in letters]
    return JSONResponse(status_code=201, content={"message": "study started"})
#progress quiz
@router.post("/result/letter")
async def letterresult(request: Request,db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")  # 쿠키 이름 확인 필요
    data = await request.json()
    if not token:
        raise HTTPException(status_code=401, detail="Token not found")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token decode failed or expired")
    
    pletters = data.get("passed", [])
    fletters = data.get("failed", [])
    if(pletters and pletters[0] == 'ㄱ') or (fletters and fletters[0] == 'ㄱ'):
        chapter_doc = await db.Chapters.find_one({"title": "자음"})
        if not chapter_doc:
            raise HTTPException(status_code=404, detail="자음 챕터를 찾을 수 없습니다")
        chapid = chapter_doc["_id"]
    elif (pletters and pletters[0] == 'ㅏ') or (fletters and fletters[0] == 'ㅏ'):
        chapter_doc = await db.Chapters.find_one({"title": "모음"})
        if not chapter_doc:
            raise HTTPException(status_code=404, detail="모음 챕터를 찾을 수 없습니다")
        chapid = chapter_doc["_id"]
    presult = []
    fresult = []
    letters = await db.Lessons.find({"chapter_id": chapid}).to_list(length=None)
    for letter in letters:
        if letter["sign_text"] in pletters:
            presult.append(letter["_id"])
        elif letter["sign_text"] in fletters:
            fresult.append(letter["_id"])
    # 모두 정답이면 quiz_correct, 하나라도 오답이면 quiz_wrong
    if pletters and not fletters:
        await db.User_Lesson_Progress.update_many(
            {
                "user_id": ObjectId(user_id),
                "lesson_id": {"$in": presult}
            },
            {"$set": {"status": "quiz_correct", "updated_at": datetime.utcnow()}}
        )
    elif fletters:
        await db.User_Lesson_Progress.update_many(
            {
                "user_id": ObjectId(user_id),
                "lesson_id": {"$in": presult + fresult}
            },
            {"$set": {"status": "quiz_wrong", "updated_at": datetime.utcnow()}}
        )
    elif not pletters and not fletters:
        await db.User_Lesson_Progress.update_many(
            {
                "user_id": ObjectId(user_id),
                "lesson_id": {"$in": [lesson["_id"] for lesson in letters]},
                "status": {"$in": ["not_started"]}
            },
            {"$set": {"status": "study", "updated_at": datetime.utcnow()}}
        )
    return {"passed": len(presult), "failed": len(fresult)}
@router.post("/study/session")
async def sessionstudy(request: Request,db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")  # 쿠키 이름 확인 필요
    data = await request.json()
    if not token:
        raise HTTPException(status_code=401, detail="Token not found")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token decode failed or expired")
    lesson_ids = [ObjectId(lesson_id) for lesson_id in data]
    # 학습 완료 처리: status를 'study', updated_at을 현재로 업데이트
    await db.User_Lesson_Progress.update_many(
        {
            "user_id": ObjectId(user_id),
            "lesson_id": {"$in": lesson_ids}
        },
        {"$set": {"status": "study", "updated_at": datetime.utcnow()}}
    )
    return JSONResponse(status_code=201, content={"message": "study started"})
@router.post("/result/session")
async def sessionresult(request: Request,db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")  # 쿠키 이름 확인 필요
    data = await request.json()
    if not token:
        raise HTTPException(status_code=401, detail="Token not found")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token decode failed or expired")
    
    correct_ids = []
    wrong_ids = []
    for result in data:
        signid = ObjectId(result.get("signId"))
        correct = result.get("correct")
        if correct:
            correct_ids.append(signid)
        else:
            wrong_ids.append(signid)
    # 모두 정답이면 quiz_correct, 하나라도 오답이면 quiz_wrong
    if correct_ids and not wrong_ids:
        await db.User_Lesson_Progress.update_many(
            {
                "user_id": ObjectId(user_id),
                "lesson_id": {"$in": correct_ids}
            },
            {"$set": {"status": "quiz_correct", "updated_at": datetime.utcnow()}}
        )
    elif wrong_ids:
        await db.User_Lesson_Progress.update_many(
            {
                "user_id": ObjectId(user_id),
                "lesson_id": {"$in": correct_ids + wrong_ids}
            },
            {"$set": {"status": "quiz_wrong", "updated_at": datetime.utcnow()}}
        )
    elif not data:
        await db.User_Lesson_Progress.update_many(
            {
                "user_id": ObjectId(user_id),
                "status": {"$in": ["not_started"]}
            },
            {"$set": {"status": "study", "updated_at": datetime.utcnow()}}
        )
    return JSONResponse(status_code=201, content={"message": "quiz complete"})

@router.get("/recent-learning")
async def get_recent_learning(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="No access token provided")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="No user id in token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")

    # last_event_at 기준으로 정렬
    progress = await db.User_Lesson_Progress.find({
        "user_id": ObjectId(user_id)
    }).sort("last_event_at", -1).limit(1).to_list(length=1)
    if not progress:
        return {"category": None, "chapter": None}
    lesson_id = progress[0]["lesson_id"]
    # 2. 레슨 정보
    lesson = await db.Lessons.find_one({"_id": lesson_id})
    if not lesson:
        return {"category": None, "chapter": None}
    # 3. 챕터 정보
    chapter = await db.Chapters.find_one({"_id": lesson["chapter_id"]})
    if not chapter:
        return {"category": None, "chapter": None}
    # 4. 카테고리 정보
    category = await db.Category.find_one({"_id": chapter["category_id"]})
    if not category:
        return {"category": None, "chapter": chapter["title"]}
    return {
        "category": category["name"],
        "chapter": chapter["title"]
    }

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

@router.post("/progress/lesson/event")
async def update_lesson_event(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")
    data = await request.json()
    lesson_ids = [ObjectId(lid) for lid in data.get("lesson_ids", [])]
    if not token:
        raise HTTPException(status_code=401, detail="Token not found")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="No user id in token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")
    await db.User_Lesson_Progress.update_many(
        {"user_id": ObjectId(user_id), "lesson_id": {"$in": lesson_ids}},
        {"$set": {"last_event_at": datetime.utcnow()}}
    )
    return {"message": "last_event_at updated"}

@router.get("/progress/overview")
async def get_progress_overview(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="No access token provided")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="No user id in token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")

    # 전체 레슨 수
    total_lessons = await db.Lessons.count_documents({})
    # reviewed 상태인 레슨 수
    reviewed_count = await db.User_Lesson_Progress.count_documents({
        "user_id": ObjectId(user_id),
        "status": "reviewed"
    })

    # 전체 진도율
    overall_progress = int((reviewed_count / total_lessons) * 100) if total_lessons > 0 else 0

    # 카테고리별 진도율 (챕터 단위)
    categories = await db.Category.find().to_list(length=None)
    category_progress = []
    for category in categories:
        # 카테고리 내 챕터 목록
        chapters = await db.Chapters.find({"category_id": category["_id"]}).to_list(length=None)
        total_chapters = len(chapters)
        completed_chapters = 0
        for chapter in chapters:
            lesson_ids = [l["_id"] for l in await db.Lessons.find({"chapter_id": chapter["_id"]}).to_list(length=None)]
            total = len(lesson_ids)
            if total == 0:
                continue
            reviewed = await db.User_Lesson_Progress.count_documents({
                "user_id": ObjectId(user_id),
                "lesson_id": {"$in": lesson_ids},
                "status": "reviewed"
            })
            if reviewed == total:
                completed_chapters += 1
        # 카테고리별 전체 레슨/완료 레슨도 기존대로 포함
        lesson_ids = [l["_id"] for l in await db.Lessons.find({"chapter_id": {"$in": [c["_id"] for c in chapters]}}).to_list(length=None)]
        total_lessons_in_cat = len(lesson_ids)
        reviewed_lessons_in_cat = await db.User_Lesson_Progress.count_documents({
            "user_id": ObjectId(user_id),
            "lesson_id": {"$in": lesson_ids},
            "status": "reviewed"
        })
        progress = int((reviewed_lessons_in_cat / total_lessons_in_cat) * 100) if total_lessons_in_cat > 0 else 0
        category_progress.append({
            "id": str(category["_id"]),
            "name": category["name"],
            "description": category.get("description", ""),
            "progress": progress,
            "completed_chapters": completed_chapters,
            "total_chapters": total_chapters,
            "completed_lessons": reviewed_lessons_in_cat,
            "total_lessons": total_lessons_in_cat,
            "status": "completed" if completed_chapters == total_chapters and total_chapters > 0 else "in_progress"
        })

    # 챕터별 완료 여부 계산 (전체)
    chapters = await db.Chapters.find().to_list(length=None)
    completed_chapter_count = 0
    for chapter in chapters:
        lesson_ids = [l["_id"] for l in await db.Lessons.find({"chapter_id": chapter["_id"]}).to_list(length=None)]
        total = len(lesson_ids)
        if total == 0:
            continue
        reviewed = await db.User_Lesson_Progress.count_documents({
            "user_id": ObjectId(user_id),
            "lesson_id": {"$in": lesson_ids},
            "status": "reviewed"
        })
        if reviewed == total:
            completed_chapter_count += 1

    return {
        "overall_progress": overall_progress,
        "completed_chapters": completed_chapter_count,
        "total_chapters": len(chapters),
        "total_lessons": total_lessons,
        "categories": category_progress
    }
