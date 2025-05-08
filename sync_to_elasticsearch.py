import os
import sys
import logging
from pymongo import MongoClient
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from dotenv import load_dotenv

# 🔧 โหลดตัวแปร .env (ถ้ามี)
load_dotenv()

# ✅ ตั้งค่า Logging
logging.basicConfig(
    filename='log_sync_to_elastic.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ✅ ตั้งค่า MongoDB และ Elasticsearch
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
ELASTIC_NODE = os.getenv("ELASTIC_NODE", "http://localhost:9200")
INDEX_NAME = "exhibitions_th"

try:
    # ✅ เชื่อม MongoDB
    client = MongoClient(MONGO_URI)
    db = client["exhibition_db"]
    exhibitions = db["exhibitions"]

    # ✅ เชื่อม Elasticsearch
    es = Elasticsearch(ELASTIC_NODE)

    # ✅ ตรวจสอบว่าเชื่อมต่อ ES ได้จริง
    if not es.ping():
        logging.error(" Elasticsearch is not reachable")
        sys.exit(1)

    # ✅ ดึงข้อมูลจาก MongoDB
    records = exhibitions.find({}, {"_id": 1, "title": 1, "description": 1})
    actions = []

    for doc in records:
        if not doc.get("title") or not doc.get("description"):
            continue  # ข้ามถ้าไม่มีข้อมูลสำคัญ
        action = {
            "_index": INDEX_NAME,
            "_id": str(doc["_id"]),
            "_source": {
                "title": doc["title"],
                "description": doc["description"]
            }
        }
        actions.append(action)

    if actions:
        # ✅ ส่งข้อมูลแบบ bulk
        success, _ = bulk(es, actions)
        logging.info(f"✔️ Synced {success} documents to Elasticsearch")
    else:
        logging.warning(" No valid documents to sync")

except Exception as e:
    logging.error(f" Error during sync: {e}")
