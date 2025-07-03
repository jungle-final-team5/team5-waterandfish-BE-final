"""
모든 Lessons 문서에 embedding(768-d) 필드를 채우는 1회성 스크립트
poetry run python scripts/backfill_embeddings.py
"""
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient, UpdateOne
from core.config import settings

BATCH_SIZE = 100
MODEL_NAME = "intfloat/multilingual-e5-base"   # 768-차원 safetensors
DB_NAME, COLL_NAME = "waterandfish", "Lessons"

model = SentenceTransformer(MODEL_NAME)
cli   = MongoClient(settings.MONGODB_URL)
col   = cli[DB_NAME][COLL_NAME]

cursor = col.find(
    {"embedding": {"$exists": False}},   # 아직 벡터 없는 문서
    {"_id": 1, "sign_text": 1}
)

bulk = []
count = 0
for doc in cursor:
    vec = model.encode(doc["sign_text"], normalize_embeddings=True).tolist()
    bulk.append(UpdateOne({"_id": doc["_id"]},
                          {"$set": {"embedding": vec}}))
    if len(bulk) >= BATCH_SIZE:
        col.bulk_write(bulk)
        count += len(bulk)
        print(f"✔  {count}개 업데이트")
        bulk = []

if bulk:
    col.bulk_write(bulk)
    count += len(bulk)

print(f"🎉  완료! 총 {count}개 문서에 embedding 필드가 추가되었습니다.")
