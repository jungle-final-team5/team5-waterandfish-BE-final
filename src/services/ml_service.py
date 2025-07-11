import os
import subprocess
# running_models: model_id(str) -> ws_url(str)
running_models = dict()
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..core.config import settings
from .model_server_manager import ModelServerManager, model_server_manager
from ..db.session import get_db
from bson import ObjectId
from collections import defaultdict

running_models = defaultdict(list)
import signal
def is_server_alive_by_pid(pid):
    try:
        if pid is None:
            return False
        # Windows
        if os.name == 'nt':
            import psutil
            return psutil.pid_exists(pid)
        # Unix
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

    # 관리 객체에서 죽은 서버 정보 정리
def cleanup_dead_servers():
    dead_ids = []
    for model_id, process in list(model_server_manager.server_processes.items()):
        pid = process.pid if process else None
        if not is_server_alive_by_pid(pid):
            dead_ids.append(model_id)
    for model_id in dead_ids:
        print(f"[CLEANUP] Removing dead server info for {model_id}")
        running_models.pop(model_id, None)
        model_server_manager.running_servers.pop(model_id, None)
        model_server_manager.server_processes.pop(model_id, None)

async def deploy_model(chapter_id, db=None, use_webrtc: bool = False):
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
    cleanup_dead_servers()

    ws_urls = []
    import re
    for model_data_url in model_data_urls:
        model_id = model_data_url
        server_alive = False
        # 직접 프로세스 상태 확인
        process = model_server_manager.server_processes.get(model_id)
        pid = process.pid if process else None
        if model_id in running_models:
            try:
                server_alive = is_server_alive_by_pid(pid)
            except Exception:
                server_alive = False
            if server_alive:
                print(f"Model server already running for {model_id}")
                ws_urls.append(running_models[model_id])
                continue
            else:
                print(f"Model server for {model_id} is not alive. Restarting...")
                running_models.pop(model_id, None)
                model_server_manager.running_servers.pop(model_id, None)
                model_server_manager.server_processes.pop(model_id, None)
        # 모델 서버 시작
        try:
            ws_url = await model_server_manager.start_model_server(model_id, model_data_url, True)
        except Exception as e:
            print(f"Failed to start model server for {model_id}: {str(e)}")
            # Continue with other models even if one fails
            raise Exception(f"Failed to start model server for {model_id}: {str(e)}")
        ws_urls.append(ws_url)
        running_models[model_id] = ws_url
        model_server_manager.running_servers[model_id] = ws_url
        server_type = "WebRTC" if use_webrtc else "WebSocket"
        print(f"{server_type} model server deployed for chapter {chapter_id}: {ws_url}")
        print(f"현재 running_models: {dict(running_models)}")
        print(f"현재 model_server_manager.running_servers: {dict(model_server_manager.running_servers)}")
        print(f"현재 model_server_manager.server_processes: {{k: v.pid if v else None for k, v in model_server_manager.server_processes.items()}}")
    
    lesson_mapper = defaultdict(str)
    for lesson in lessons:
        lesson_mapper[str(lesson["_id"])] = running_models[lesson["model_data_url"]]
    print('[ml_service]lesson_mapper', lesson_mapper)
    return ws_urls, lesson_mapper

# 단일 레슨 모델 서버 배포
async def deploy_lesson_model(lesson_id, db=None, use_webrtc: bool = False):
    from bson import ObjectId
    if db is None:
        db = await get_db().__anext__()
    obj_id = ObjectId(lesson_id)
    lesson = await db.Lessons.find_one({"_id": obj_id})
    if not lesson:
        raise Exception(f"Lesson with id {lesson_id} not found")
    model_data_url = lesson.get("model_data_url")
    if not model_data_url:
        raise Exception(f"Lesson {lesson_id} does not have a model_data_url")
    model_id = model_data_url
    import re
    if model_id in running_models:
        ws_url = running_models[model_id]
    else:
        ws_url = await model_server_manager.start_model_server(model_id, model_data_url, use_webrtc)
        running_models[model_id] = ws_url
        match = re.search(r":(\d+)/ws", ws_url)
        if match:
            port = int(match.group(1))
            model_server_manager.running_servers[model_id] = port
    return ws_url