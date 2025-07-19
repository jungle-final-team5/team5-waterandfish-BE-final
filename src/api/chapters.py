from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.session import get_db
from .utils import get_user_id_from_token, convert_objectid

router = APIRouter(prefix="/chapters", tags=["chapters"])

CHAPTER_TYPES = ["word", "sentence"]



@router.post("")
async def create_chapter(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    """챕터 생성"""
    data = await request.json()
    
    if "title" not in data or "categoryid" not in data or "type" not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Missing required fields: title, categoryid, type"
        )
    
    if data["type"] not in CHAPTER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid type: {data['type']}"
        )
    
    try:
        category_id = ObjectId(data["categoryid"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid category ID"
        )
    
    category = await db.Category.find_one({"_id": category_id})
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Category not found"
        )
    
    chapter_data = {
        "category_id": category["_id"],
        "title": data["title"],
        "lesson_type": data["type"],
        "order_index": 0,
        "description": None,
        "created_at": datetime.utcnow()
    }
    
    result = await db.Chapters.insert_one(chapter_data)
    created = await db.Chapters.find_one({"_id": result.inserted_id})
    created.pop("created_at", None)
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=convert_objectid(created)
    )
    
@router.post("/v2")
async def create_chapter(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    """챕터 생성"""
    data = await request.json()
    
    if "title" not in data or "categoryid" not in data or "type" not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Missing required fields: title, categoryid, type"
        )
    
    if data["type"] not in CHAPTER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid type: {data['type']}"
        )
    if data["course_type"] not in [1, 2]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid course type: {data['course_type']}"
        )
    
    lesson_ids = [ObjectId(lid) for lid in data["lesson_ids"]]
    
    try:
        category_id = ObjectId(data["categoryid"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid category ID"
        )
    
    category = await db.Category.find_one({"_id": category_id})
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Category not found"
        )
    
    chapter_data = {
        "category_id": category["_id"],
        "title": data["title"],
        "lesson_type": data["type"],
        "order_index": 0,
        "description": None,
        "created_at": datetime.utcnow(),
        "course_type": data["course_type"],
        "lesson_ids": lesson_ids
    }
    
    result = await db.Chapters.insert_one(chapter_data)
    created = await db.Chapters.find_one({"_id": result.inserted_id})
    created.pop("created_at", None)
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=convert_objectid(created)
    )

@router.get("")
async def get_all_chapters(db: AsyncIOMotorDatabase = Depends(get_db)):
    """모든 챕터 조회 (각 챕터별 lesson 포함, order_index 기준 정렬)"""
    print('[get_all_chapters] flag 1')
    chapters = await db.Chapters.find().sort("order_index", 1).to_list(length=None)
    print('[get_all_chapters] flag 2')
    result = []
    for chapter in chapters:
        lessons = await db.Lessons.find({"chapter_id": chapter["_id"]}).to_list(length=None)
        lesson_list = []
        for lesson in lessons:
            item = {
                "id": str(lesson["_id"]),
                "chapterId": str(lesson["chapter_id"]),
                "word": lesson.get("sign_text", ""),
                "type": lesson.get("content_type", "")
            }
            if "model_data_url" in lesson:
                item["modelInfo"] = lesson["model_data_url"]
            if "media_url" in lesson:
                item["url"] = lesson["media_url"]
            if "created_at" in lesson and isinstance(lesson["created_at"], datetime):
                item["created_at"] = lesson["created_at"].isoformat()
            lesson_list.append(item)
        chapter_data = convert_objectid(chapter)
        chapter_data["lessons"] = lesson_list
        result.append(chapter_data)
    print('[get_all_chapters] flag 3')
    return {
        "success": True,
        "data": {"chapters": result},
        "message": "챕터 목록(레슨 포함, order_index 정렬) 조회 성공"
    }
    
@router.get("/v2")
async def get_all_chapters_v2(db: AsyncIOMotorDatabase = Depends(get_db)):
    chapters = await db.Chapters.find().to_list(length=None)
    result = []
    for chapter in chapters:
        lesson_list = []
        lessons = await db.Lessons.find({"_id": {"$in": chapter["lesson_ids"]}}, {"embedding": 0}).to_list(length=None)
        for lesson in lessons:
            item = {
                "id": str(lesson["_id"]),
                "chapterId": str(lesson["chapter_id"]),
                "word": lesson.get("sign_text", ""),
                "type": lesson.get("content_type", "")
            }
            if "model_data_url" in lesson:
                item["modelInfo"] = lesson["model_data_url"]
            if "media_url" in lesson:
                item["url"] = lesson["media_url"]
            if "created_at" in lesson and isinstance(lesson["created_at"], datetime):
                item["created_at"] = lesson["created_at"].isoformat()
            lesson_list.append(item)
        chapter_data = convert_objectid(chapter)
        chapter_data["lessons"] = lesson_list
        result.append(chapter_data)
    return {
        "success": True,
        "data": {"chapters": result},
        "message": "챕터 목록(레슨 포함, order_index 정렬) 조회 성공"
    }

@router.get("/{chapter_id}")
async def get_chapter(
    chapter_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """특정 챕터 조회"""
    try:
        obj_id = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid chapter ID"
        )
    print('[get_chapter] chapter_id:', chapter_id)
    chapter = await db.Chapters.find_one({"_id": obj_id})
    print('[get_chapter] chapter:', chapter)
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chapter not found"
        )
    
    return {
        "success": True,
        "data": {"type": chapter.get("title", "기타")},
        "message": "챕터 조회 성공"
    }

@router.put("/{chapter_id}")
async def update_chapter(
    chapter_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """챕터 수정"""
    data = await request.json()
    
    try:
        obj_id = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid chapter ID"
        )
    
    update_data = {}
    if "title" in data:
        update_data["title"] = data["title"]
    if "type" in data:
        if data["type"] not in CHAPTER_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Invalid type: {data['type']}"
            )
        update_data["lesson_type"] = data["type"]
    if "description" in data:
        update_data["description"] = data["description"]
    if "order_index" in data:
        update_data["order_index"] = data["order_index"]
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No fields to update"
        )
    
    result = await db.Chapters.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chapter not found"
        )
    
    return {
        "success": True,
        "message": "챕터 수정 성공"
    }

@router.delete("/{chapter_id}")
async def delete_chapter(
    chapter_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """챕터 삭제"""
    try:
        obj_id = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid chapter ID"
        )
    
    # 연관된 레슨도 함께 삭제
    # await db.Lessons.delete_many({"chapter_id": obj_id})
    
    result = await db.Chapters.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chapter not found"
        )
    
    return {
        "success": True,
        "message": "챕터 삭제 성공"
    }

@router.post("/{chapter_id}/lessons/connect")
async def connect_lessons_to_chapter(
    chapter_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """챕터에 레슨 연결"""
    data = await request.json()
    
    try:
        chapter_obj_id = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid chapter ID"
        )
    
    lesson_ids = data.get("lesson", [])
    lesson_obj_ids = [ObjectId(lid) for lid in lesson_ids]
    course_type = data.get("course_type", 1)
    
    chapter = await db.Chapters.find_one({"_id": chapter_obj_id})
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chapter not found"
        )
    await db.Chapters.update_one(
        {"_id": chapter_obj_id},
        {"$set": {"course_type": course_type, "lesson_ids": lesson_obj_ids}}
    )   
    
    # 기존 연결 해제
    await db.Lessons.update_many(
        {"chapter_id": chapter_obj_id},
        {"$set": {"chapter_id": None}}
    )
    
    # 새로운 연결 설정
    if lesson_obj_ids:
        await db.Lessons.update_many(
            {"_id": {"$in": lesson_obj_ids}},
            {"$set": {"chapter_id": chapter_obj_id}}
        )
    
    return {
        "success": True,
        "message": "레슨 연결 성공"
    }

@router.get("/{chapter_id}/session")
async def get_chapter_session(
    chapter_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """챕터 학습 세션 조회 - /chapters/{chapter_id}/session"""
    user_id = get_user_id_from_token(request)
    try:
        obj_id = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid chapter ID"
        )
    chapter = await db.Chapters.find_one({"_id": obj_id})
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chapter not found"
        )
    lessons = await db.Lessons.find({"_id": {"$in": chapter["lesson_ids"]}}, {"embedding": 0}).to_list(length=None)
    lesson_ids = [lesson["_id"] for lesson in lessons]
    lesson_status_map = {}
    if user_id and lesson_ids:
        progresses = await db.User_Lesson_Progress.find({
            "user_id": ObjectId(user_id),
            "lesson_id": {"$in": lesson_ids}
        }).to_list(length=None)
        progress_dict = {str(p["lesson_id"]): p for p in progresses}
        # 누락된 User_Lesson_Progress 자동 생성
        missing = [lesson_id for lesson_id in lesson_ids if str(lesson_id) not in progress_dict]
        if missing:
            now = datetime.utcnow()
            await db.User_Lesson_Progress.insert_many([
                {
                    "user_id": ObjectId(user_id),
                    "lesson_id": lesson_id,
                    "status": "not_started",
                    "updated_at": now
                } for lesson_id in missing
            ])
            # 다시 조회
            progresses = await db.User_Lesson_Progress.find({
                "user_id": ObjectId(user_id),
                "lesson_id": {"$in": lesson_ids}
            }).to_list(length=None)
            progress_dict = {str(p["lesson_id"]): p for p in progresses}
        for progress in progresses:
            lesson_status_map[str(progress["lesson_id"])] = progress.get("status", "not_started")
    lesson_list = []
    for lesson in lessons:
        lesson_list.append({
            "id": str(lesson["_id"]),
            "word": lesson.get("sign_text", ""),
            "videoUrl": str(lesson.get("media_url", "")),
            "description": lesson.get("description", ""),
            "status": lesson_status_map.get(str(lesson["_id"]), "not_started")
        })
    category = await db.Category.find_one({"_id": chapter["category_id"]})
    result = {
        "id": str(chapter["_id"]),
        "title": chapter["title"],
        "type": chapter.get("lesson_type", None),
        "category_name": category["name"] if category else "Unknown",
        "lessons": lesson_list,
        "order_index": chapter.get("order_index", 0)
    }
    return {
        "success": True,
        "data": result,
        "message": "챕터 학습 세션 조회 성공"
    }
    
@router.get("/v2/{chapter_id}")
async def get_chapter_v2(
    chapter_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """챕터 조회"""
    chapter = await db.Chapters.find_one({"_id": ObjectId(chapter_id)})
    encoded_chapter = convert_objectid(chapter)
    
    return {    
        "success": True,
        "data": encoded_chapter,
        "message": "챕터 조회 성공"
    }
            
@router.get("/{chapter_id}/guide")
async def get_chapter_guide(
    chapter_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """챕터 학습 가이드 조회 - /chapters/{chapter_id}/guide"""
    try:
        obj_id = ObjectId(chapter_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid chapter ID"
        )
    chapter = await db.Chapters.find_one({"_id": obj_id})
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chapter not found"
        )
    category = await db.Category.find_one({"_id": chapter["category_id"]})
    lessons = await db.Lessons.find({"chapter_id": obj_id}).to_list(length=None)
    lesson_list = []
    for lesson in lessons:
        lesson_list.append({
            "id": str(lesson["_id"]),
            "word": lesson.get("sign_text", ""),
            "videoUrl": str(lesson.get("media_url", "")),
            "description": lesson.get("description", ""),
            "order_index": lesson.get("order_index", 0)
        })
    result = {
        "id": str(chapter["_id"]),
        "title": chapter["title"],
        "type": chapter.get("lesson_type", None),
        "category_name": category["name"] if category else "Unknown",
        "description": chapter.get("description", ""),
        "lessons": lesson_list,
        "order_index": chapter.get("order_index", 0)
    }
    return {
        "success": True,
        "data": result,
        "message": "챕터 학습 가이드 조회 성공"
    } 