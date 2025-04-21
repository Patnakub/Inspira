from datetime import datetime
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["exhibition_db"]
collection = db["exhibitions"]

now = datetime.now()

# อัปเดตเป็น ongoing
collection.update_many({
    "start_date_obj": {"$lte": now},
    "end_date_obj": {"$gte": now}
}, { "$set": { "status": "ongoing" }})

# อัปเดตเป็น upcoming
collection.update_many({
    "start_date_obj": {"$gt": now}
}, { "$set": { "status": "upcoming" }})

# อัปเดตเป็น past
collection.update_many({
    "end_date_obj": {"$lt": now}
}, { "$set": { "status": "past" }})

print("✅ อัปเดต status รายวันเสร็จสิ้น")
