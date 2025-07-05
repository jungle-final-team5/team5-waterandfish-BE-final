import os
import subprocess
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..core.config import settings
from .model_server_manager import ModelServerManager, model_server_manager
from ..db.session import get_db

running_models = {}

async def deploy_model(chapter_id, db: AsyncIOMotorDatabase = None):
    """챕터에 해당하는 모델 서버를 배포"""
    if db is None:
        # db가 없으면 새로 가져오기 (이상적으로는 의존성 주입 사용)
        db = await get_db().__anext__()
    
    # 챕터 정보 조회
    chapter = await db.Chapters.find_one({"_id": chapter_id})
    if not chapter:
        raise Exception(f"Chapter with id {chapter_id} not found")
    
    # 해당 챕터의 레슨들 조회
    lessons = await db.Lessons.find({"chapter_id": chapter_id}).to_list(length=None)
    
    # 모델 데이터 URL이 있는 레슨 확인
    model_data_urls = [lesson.get("model_data_url") for lesson in lessons if lesson.get("model_data_url")]

    ws_urls = []
    for model_data_url in model_data_urls:
        model_id = model_data_url
        
        if model_id in running_models: # 이미 실행중인 모델이면 웹소켓 주소 추가
            ws_urls.append(running_models[model_id]) 
        else: # 모델 서버 시작
            try:
                ws_url = await model_server_manager.start_model_server(model_id, model_data_url)
            except Exception as e:
                print(f"Failed to start model server for {model_id}: {str(e)}")
                # Continue with other models even if one fails
                raise Exception(f"Failed to start model server for {model_id}: {str(e)}")
            ws_urls.append(ws_url)
            print(f"Model server deployed for chapter {chapter_id}: {ws_url}")
            
    
    return ws_urls