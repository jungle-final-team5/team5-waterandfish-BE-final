"""
모든 Lessons 문서에 embedding(768-d)을 ‘덮어쓰기’로 채우는 스크립트
poetry run python src/scripts/seed_embeddings.py
"""
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient, UpdateOne
from core.config import settings

MODEL_NAME = "intfloat/multilingual-e5-base"
BATCH_SIZE = 100
DB, COLL   = "waterandfish", "Lessons"

def normalize_sign_text(raw):
    if isinstance(raw, str):
        return raw
    if raw is None:
        return ""
    if isinstance(raw, (int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("ko") or raw.get("en") or next(iter(raw.values()), ""))
    if isinstance(raw, (list, tuple, set)):
        return normalize_sign_text(next(iter(raw), ""))
    return str(raw)

model = SentenceTransformer(MODEL_NAME)
col   = MongoClient(settings.MONGODB_URL)[DB][COLL]

cursor = col.find(
    { "sign_text": { "$type": "string" } },      # ← 문자열만!
    { "_id": 1, "sign_text": 1 }
)

bulk, processed = [], 0
for doc in cursor:
    text = normalize_sign_text(doc["sign_text"])
    if not text:            # 빈 문자열이면 생략
        continue
    vec = model.encode(text, normalize_embeddings=True).tolist()

    bulk.append(UpdateOne(
        { "_id": doc["_id"] },
        { "$set": { "embedding": vec } }
    ))

    if len(bulk) >= BATCH_SIZE:
        col.bulk_write(bulk)
        processed += len(bulk)
        print(f"✔  {processed}개 처리")
        bulk = []

if bulk:
    col.bulk_write(bulk)
    processed += len(bulk)

print(f"🎉  완료! 총 {processed}개 문서의 embedding이 갱신되었습니다.")
