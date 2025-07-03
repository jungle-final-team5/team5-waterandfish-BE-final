from sentence_transformers import SentenceTransformer
from pymongo import MongoClient, UpdateOne
from core.config import settings

URI  = settings.MONGODB_URL
DB, COL = "waterandfish", "Lessons"
BATCH = 100
model = SentenceTransformer("intfloat/multilingual-e5-base")

cli  = MongoClient(URI)
col  = cli[DB][COL]

bulk = []
for doc in col.find({}, {"_id": 1, "sign_text": 1}):  # 모든 문서 대상으로 변경
    vec = model.encode(doc["sign_text"], normalize_embeddings=True).tolist()
    bulk.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"embedding": vec}}))
    if len(bulk) == BATCH:
        col.bulk_write(bulk); bulk = []
if bulk:
    col.bulk_write(bulk)

print("✅  embeddings inserted")
