from fastapi import APIRouter, HTTPException, Depends
from typing import List
from odmantic import AIOEngine, ObjectId
from team5_waterandfish_be.models.user import User, Handedness
from team5_waterandfish_be.db.session import get_engine
import hashlib

router = APIRouter(prefix="/users", tags=["users"])

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@router.post("/", response_model=User)
async def create_user(user: User, engine: AIOEngine = Depends(get_engine)):
    user.password_hash = hash_password(user.password_hash)
    await engine.save(user)
    return user

@router.get("/", response_model=List[User])
async def list_users(engine: AIOEngine = Depends(get_engine)):
    users = await engine.find(User)
    return users

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, engine: AIOEngine = Depends(get_engine)):
    user = await engine.find_one(User, User.id == ObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=User)
async def update_user(user_id: str, user_update: User, engine: AIOEngine = Depends(get_engine)):
    user = await engine.find_one(User, User.id == ObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    await engine.save(user)
    return user

@router.delete("/{user_id}")
async def delete_user(user_id: str, engine: AIOEngine = Depends(get_engine)):
    user = await engine.find_one(User, User.id == ObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await engine.delete(user)
    return {"ok": True} 