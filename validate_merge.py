import os
import json
import pandas as pd
import re
from datetime import datetime

# --------------------------
# 📍 CONFIG
# --------------------------
merge_dir = "merge_data"

# --------------------------
# 🔄 หาไฟล์ล่าสุดในโฟลเดอร์ merge_data
# --------------------------
all_files = sorted(
    [f for f in os.listdir(merge_dir) if f.startswith("merged_full") and f.endswith(".json")],
    key=lambda x: os.path.getmtime(os.path.join(merge_dir, x)),
    reverse=True
)
if not all_files:
    print("❌ ไม่พบไฟล์ .json ใน merge_data/")
    exit()

latest_file = all_files[0]
path = os.path.join(merge_dir, latest_file)
print(f"📂 กำลังตรวจไฟล์: {latest_file}")

# --------------------------
# 📥 โหลด JSON เข้า DataFrame
# --------------------------
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
df = pd.DataFrame(data)

# --------------------------
# 🔍 ตรวจ NULL, ค่าว่าง, หรือคำไม่สื่อความหมาย
# --------------------------
print("\n🔍 ฟิลด์ที่เป็น null/NaN:")
print(df.isnull().sum())

print("\n🔍 ฟิลด์ที่มีค่าเป็น 'null', 'none', 'ไม่มีข้อมูล', 'ไม่ระบุ':")
null_like_words = {"", "null", "none", "ไม่มีข้อมูล", "ไม่ระบุ", "-", "n/a"}
for col in df.columns:
    if df[col].dtype == 'object':
        null_like = df[col].astype(str).str.strip().str.lower().isin(null_like_words)
        count = null_like.sum()
        if count > 0:
            print(f"- {col}: {count} ค่า")

# --------------------------
# 🎟️ ตรวจ ticket_price ว่าต้องเป็น list ของตัวเลข หรือว่าง
# --------------------------
print("\n🎟️ ตรวจ ticket_price ว่าถูกต้องไหม (ควรเป็น list หรือ NaN):")
bad_prices = df[~df["ticket_price"].apply(lambda x: isinstance(x, list) or pd.isna(x))]
if not bad_prices.empty:
    print(f"❌ พบ {len(bad_prices)} ค่าไม่ถูกต้อง:")
    print(bad_prices[["title", "ticket_price"]])
else:
    print("✅ ticket_price ถูกต้องทั้งหมด")

# --------------------------
# 📌 ตรวจ status
# --------------------------
print("\n📌 ค่าที่พบใน status:")
print(df["status"].value_counts())

allowed_status = {"upcoming", "ongoing", "past"}
invalid_status = df[~df["status"].isin(allowed_status)]
if not invalid_status.empty:
    print(f"❌ พบค่าที่ไม่ถูกต้องใน status: {invalid_status['status'].unique()}")

# --------------------------
# 🗓️ ตรวจรูปแบบวันที่ไทย (22 มกราคม 2025)
# --------------------------
thai_months = {
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
}

def is_valid_date_format(date_str):
    if not isinstance(date_str, str):
        return False
    match = re.match(r"^\d{1,2} ([ก-๙]+) (\d{4})$", date_str.strip())
    if not match:
        return False
    month = match.group(1)
    year = int(match.group(2))
    if month not in thai_months:
        return False
    if year < 2020 or year > 2100:
        return False
    return True

def check_date_column(colname):
    print(f"\n🗓️ ตรวจรูปแบบวันที่ใน '{colname}'...")
    invalid = df[~df[colname].apply(is_valid_date_format)]
    if not invalid.empty:
        print(f"❌ พบ {len(invalid)} รายการที่รูปแบบวันที่ไม่ถูกต้อง:")
        print(invalid[[colname, "title"]])
    else:
        print("✅ รูปแบบวันที่ถูกต้องทั้งหมด")

check_date_column("start_date")
check_date_column("end_date")

# --------------------------
# 🧠 ตรวจ title ซ้ำ
# --------------------------
print("\n🧠 ตรวจ title ซ้ำ:")
duplicate_titles = df[df.duplicated("title", keep=False)]
if not duplicate_titles.empty:
    print(f"❌ พบ title ซ้ำจำนวน {len(duplicate_titles)} รายการ")
    print(duplicate_titles[["title", "start_date", "source_file"]])
else:
    print("✅ ไม่พบ title ซ้ำ")

# --------------------------
# ✅ สรุป
# --------------------------
print("\n🎉 เสร็จสิ้นการตรวจสอบ")
