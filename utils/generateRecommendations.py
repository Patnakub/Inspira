# -*- coding: utf-8 -*-
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
from datetime import datetime
import sys

client = MongoClient("mongodb://localhost:27017")  # แก้เป็น MongoDB URI ของนายถ้าใช้ Atlas
db = client["exhibition_db"]
exhibitions_col = db["exhibitions"]
users_col = db["users"]
recommendations_col = db["recommendations"]

# ดึง categories จาก collection
categories_cursor = db["categories"].find({})
categories = sorted([doc['name'] for doc in categories_cursor])


# 🧠 ดึงนิทรรศการที่ยังไม่จบ
exhibitions = list(exhibitions_col.find({
    "status": { "$in": ["ongoing", "upcoming"] }
}))

events_df = pd.DataFrame(exhibitions)
events_df['_id'] = events_df['_id'].astype(str)
events_df = events_df.rename(columns={'_id': 'event_id'})

# สร้างเวกเตอร์หมวดหมู่จาก field 'categories'
for c in categories:
    events_df[c] = events_df['categories'].apply(lambda lst: int(c in lst) if isinstance(lst, list) else 0)

# 🧠 ดึงผู้ใช้ทั้งหมด
users = list(users_col.find({}))
users_df = pd.DataFrame([{
    'username': u['username'],
    'user_id': str(u['_id']),
    **{c: int(c in u.get('interests', [])) for c in categories}
} for u in users])

# 💡 เวกเตอร์หมวดหมู่
event_vectors = events_df[categories]
user_vectors = users_df[categories]

# 🧠 คำนวณความคล้าย
similarity_matrix = cosine_similarity(user_vectors, event_vectors)

# ล้างข้อมูลเดิม
recommendations_col.delete_many({})

# สร้างผลลัพธ์ใหม่
for i, user in users_df.iterrows():
    user_id = user['user_id']
    similarities = similarity_matrix[i]

    recs = []
    for j, score in enumerate(similarities):
        recs.append({
            "event_id": events_df.iloc[j]['event_id'],
            "score": round(score, 4)
        })

    recs.sort(key=lambda x: x['score'], reverse=True)

    recommendations_col.insert_one({
        "user_id": user_id,
        "recommendations": recs,
        "updated_at": datetime.utcnow()
    })

sys.stdout.buffer.write("บันทึกคำแนะนำลง MongoDB เรียบร้อยแล้ว\n".encode('utf-8'))
