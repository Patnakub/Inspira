# -*- coding: utf-8 -*-
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
from datetime import datetime
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

start_time = time.time()

# --------------------------
# ✅ CONFIG
# --------------------------
MONGO_URI = "mongodb+srv://inspiraproject2025:ypLEu0xL3plfo2AW@exhibition-cluster.ty3ugcy.mongodb.net/exhibition_db"
client = MongoClient(MONGO_URI)

db = client["exhibition_db"]
exhibitions_col = db["exhibitions"]
users_col = db["users"]
recommendations_col = db["recommendations"]
categories_cursor = db["categories"].find({})
categories = sorted([doc['name'] for doc in categories_cursor])

# --------------------------
# 📦 Load Exhibitions
# --------------------------
exhibitions = list(exhibitions_col.find({
    "status": { "$in": ["ongoing", "upcoming"] }
}))
events_df = pd.DataFrame(exhibitions)
events_df['_id'] = events_df['_id'].astype(str)
events_df = events_df.rename(columns={'_id': 'event_id'})

for c in categories:
    events_df[c] = events_df['categories'].apply(lambda lst: int(c in lst) if isinstance(lst, list) else 0)

# --------------------------
# 👤 Load Users
# --------------------------
users = list(users_col.find({}))
users_df = pd.DataFrame([{
    'username': u['username'],
    'user_id': str(u['_id']),
    **{c: int(c in u.get('interests', [])) for c in categories}
} for u in users])

if users_df.empty or events_df.empty:
    print("⚠️ ไม่มีข้อมูลผู้ใช้หรือข้อมูลนิทรรศการ")
    sys.exit(0)

# --------------------------
# 🤖 Calculate Similarity
# --------------------------
event_vectors = events_df[categories]
user_vectors = users_df[categories]
similarity_matrix = cosine_similarity(user_vectors, event_vectors)

# --------------------------
# 🧹 Clear old recommendations
# --------------------------
recommendations_col.delete_many({})
bulk_data = []

# --------------------------
# 📌 Generate New Recommendations
# --------------------------
for i, user in users_df.iterrows():
    print(f" กำลังประมวลผลผู้ใช้ {i+1}/{len(users_df)}")

    user_id = user['user_id']
    similarities = similarity_matrix[i]

    recs = [{
        "event_id": events_df.iloc[j]['event_id'],
        "score": round(score, 4)
    } for j, score in enumerate(similarities)]

    recs.sort(key=lambda x: x['score'], reverse=True)

    bulk_data.append({
        "user_id": user_id,
        "recommendations": recs,
        "updated_at": datetime.utcnow()
    })

# --------------------------
# 🚀 Upload to MongoDB
# --------------------------
recommendations_col.insert_many(bulk_data)

# --------------------------
# ✅ Done
# --------------------------
duration = round(time.time() - start_time, 2)
sys.stdout.buffer.write(f"✅ บันทึกคำแนะนำทั้งหมดเรียบร้อยแล้ว ใช้เวลา {duration} วินาที\n".encode('utf-8'))
