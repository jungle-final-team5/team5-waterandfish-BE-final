from sentence_transformers import SentenceTransformer
from pymongo import MongoClient, UpdateOne
from core.config import settings

BATCH_SIZE = 100
MODEL_NAME = "intfloat/multilingual-e5-base"
DB_NAME, COLL_NAME = "waterandfish", "Lessons"

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
col   = MongoClient(settings.MONGODB_URL)[DB_NAME][COLL_NAME]

cursor = col.find(
    {
        "embedding": {"$exists": False},
        "sign_text": {"$type": "string"}   # <-- 문자열만!
    },
    {"_id": 1, "sign_text": 1}
)

bulk, count = [], 0
for doc in cursor:
    text = normalize_sign_text(doc["sign_text"])
    if not text:
        continue
    vec = model.encode(text, normalize_embeddings=True).tolist()
    bulk.append(UpdateOne({"_id": doc["_id"]},
                          {"$set": {"embedding": vec}}))
    if len(bulk) >= BATCH_SIZE:
        col.bulk_write(bulk)
        count += len(bulk)
        print(f"✔ {count}개 업데이트")
        bulk = []

if bulk:
    col.bulk_write(bulk)
    count += len(bulk)

print(f"🎉 완료! 총 {count}개 문서에 embedding 필드가 추가되었습니다.")
