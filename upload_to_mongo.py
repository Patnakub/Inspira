import os
import json
import glob
import pymongo
from datetime import datetime

# -----------------------
# CONFIG
# -----------------------
MONGO_URI = "mongodb+srv://inspiraproject2025:ypLEu0xL3plfo2AW@exhibition-cluster.ty3ugcy.mongodb.net/exhibition_db"
DB_NAME = "exhibition_db"
COLLECTION_NAME = "exhibitions"
MERGE_DIR = "./merge_data"

# -----------------------
# Connect MongoDB
# -----------------------
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# -----------------------
# Find latest merged_*.json
# -----------------------
files = glob.glob(os.path.join(MERGE_DIR, "merged_*.json"))
if not files:
    print("No merged_*.json files found in merge_data/")
    exit(1)

latest_file = max(files, key=os.path.getmtime)
print(f"Use file: {os.path.basename(latest_file)}")

# -----------------------
# Load data from JSON
# -----------------------
with open(latest_file, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Load all {len(data)} items")

# -----------------------
# Insert or Update
# -----------------------
inserted, updated, skipped = 0, 0, 0

for item in data:
    title = item.get("title")
    start_date = item.get("start_date")
    location = item.get("location")

    # แปลง date_obj เป็น datetime object
    for date_key in ["start_date_obj", "end_date_obj"]:
        if date_key in item and isinstance(item[date_key], str):
            try:
                item[date_key] = datetime.fromisoformat(item[date_key])
            except:
                item[date_key] = None

    # ตรวจสอบว่าซ้ำหรือไม่
    existing = collection.find_one({
        "title": title,
        "start_date": start_date,
        "location": location
    })

    if not existing:
        item["category_verified"] = False
        collection.insert_one(item)
        inserted += 1
    else:
        update_fields = {}

        # ✅ อัปเดตเฉพาะ field ที่ปลอดภัย
        if len(str(item.get("description") or "")) > len(str(existing.get("description") or "")):
            update_fields["description"] = item["description"]

        for key in ["cover_picture", "url", "ticket", "ticket_price"]:
            if not existing.get(key) and item.get(key):
                update_fields[key] = item[key]

        for key in ["latitude", "longitude"]:
            if not existing.get(key) and item.get(key):
                update_fields[key] = item[key]

        for key in ["start_date_obj", "end_date_obj"]:
            if item.get(key) and item.get(key) != existing.get(key):
                update_fields[key] = item[key]

        if item.get("status") != existing.get("status"):
            update_fields["status"] = item.get("status")

        if not existing.get("category_verified", False):
            update_fields["categories"] = item.get("categories")

        if update_fields:
            collection.update_one({"_id": existing["_id"]}, {"$set": update_fields})
            updated += 1
        else:
            skipped += 1

print(f"New added: {inserted} | Updated: {updated} | Skipped: {skipped}")
