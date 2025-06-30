from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db

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
        "media_url": None,
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
                    "description": sign.get("description", "")
                })
            
            chapter_list.append({
                "id": str(chapter["_id"]),
                "title": chapter["title"],
                "type": chapter.get("type", None),  # type이 없으면 None 반환
                "signs": sign_list,
                "categoryId": str(category_id)
            })
        
        results.append({
            "id": str(c["_id"]),
            "title": c["name"],
            "description": c["description"],
            "chapters": chapter_list,
            "icon": "📚"  # 기본 아이콘
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
                "description": sign.get("description", "")
            })
        
        chapterresult.append({
            "id": str(c["_id"]),
            "title": c["title"],
            "type": c.get("type", None),  # type이 없으면 None 반환
            "signs": sign_list,
            "categoryId": str(obj_id)
        })

    result = {
        "id": str(cate["_id"]),
        "title": cate["name"],
        "description": cate["description"],
        "chapters": chapterresult,
        "icon": "📚"
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