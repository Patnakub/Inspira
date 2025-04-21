# merge_pipeline.py
import os
import json
import pandas as pd
from glob import glob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from collections import defaultdict
import dateparser
import sys
from datetime import datetime
import re

# ------------------------
# CONFIG
# ------------------------
base_path = os.path.abspath("./scrapy_project/spiders")
eps = 0.3  # ปรับความเข้มงวดของ clustering

# ------------------------
# Helper Functions
# ------------------------
def is_empty(value):
    return value in [None, "", "null", "NULL", "-", [], {}] or (
        isinstance(value, str) and value.strip().lower() == "null"
    )

def normalize_field(key, value):
    if key == "ticket_price":
        if isinstance(value, str) and value.isdigit():
            return [int(value)]
        if isinstance(value, int):
            return [value]
    return value

def get_year_from_date(date_str):
    dt = dateparser.parse(date_str, languages=['th', 'en'])
    return dt.year if dt else None

# ------------------------
# Merge Logic
# ------------------------
def smart_merge_fully_matched(a, b):
    merged = {}
    skip_ticket_price = False
    reliability_a = a.get("reliability_score", 0)
    reliability_b = b.get("reliability_score", 0)
    timestamp_a = a.get("timestamp", "")
    timestamp_b = b.get("timestamp", "")

    for key in set(a.keys()).union(b.keys()):
        a_val = normalize_field(key, a.get(key))
        b_val = normalize_field(key, b.get(key))

        if key == "ticket_price" and skip_ticket_price:
            continue

        if key == "ticket":
            if str(a_val).strip() == "มีค่าเข้าชม":
                merged["ticket"] = a_val
                merged["ticket_price"] = normalize_field("ticket_price", a.get("ticket_price"))
                skip_ticket_price = True
                continue
            elif str(b_val).strip() == "มีค่าเข้าชม":
                merged["ticket"] = b_val
                merged["ticket_price"] = normalize_field("ticket_price", b.get("ticket_price"))
                skip_ticket_price = True
                continue
            else:
                merged["ticket"] = a_val if reliability_a >= reliability_b else b_val
                continue

        if key == "title":
            if reliability_a > reliability_b:
                merged[key] = a_val
            elif reliability_b > reliability_a:
                merged[key] = b_val
            else:
                merged[key] = a_val if timestamp_a > timestamp_b else b_val
            continue

        if is_empty(a_val) and not is_empty(b_val):
            merged[key] = b_val
        elif not is_empty(a_val) and is_empty(b_val):
            merged[key] = a_val
        elif key == "status":
            if a_val != b_val:
                if reliability_a > reliability_b:
                    merged[key] = a_val
                elif reliability_b > reliability_a:
                    merged[key] = b_val
                else:
                    merged[key] = a_val if timestamp_a > timestamp_b else b_val
            else:
                merged[key] = a_val
    
        elif not is_empty(a_val) and not is_empty(b_val):
            if key == "description":
                merged[key] = a_val if len(str(a_val)) >= len(str(b_val)) else b_val
                merged["categories"] = a.get("categories") if len(str(a_val)) >= len(str(b_val)) else b.get("categories")
            elif key in ["url", "cover_picture"]:
                if reliability_a > reliability_b:
                    merged[key] = a_val
                elif reliability_b > reliability_a:
                    merged[key] = b_val
                else:
                    merged[key] = a_val if timestamp_a > timestamp_b else b_val
            elif key not in ["categories"]:
                merged[key] = a_val if len(str(a_val)) >= len(str(b_val)) else b_val
        else:
            merged[key] = None

    return merged

def compare_records(a, b):
    merged = {}
    reliability_a = a.get("reliability_score", 0)
    reliability_b = b.get("reliability_score", 0)
    timestamp_a = a.get("timestamp", "")
    timestamp_b = b.get("timestamp", "")

    core_fields = ["start_date", "end_date", "location"]
    all_core_equal = all(a.get(f, "") == b.get(f, "") for f in core_fields)

    if all_core_equal:
        return smart_merge_fully_matched(a, b)

    for field in core_fields:
        a_val = a.get(field)
        b_val = b.get(field)
        if a_val == b_val:
            merged[field] = a_val
        else:
            if reliability_a > reliability_b:
                merged[field] = a_val
            elif reliability_b > reliability_a:
                merged[field] = b_val
            else:
                merged[field] = a_val if timestamp_a > timestamp_b else b_val

    other_merged = smart_merge_fully_matched(a, b)
    for key, val in other_merged.items():
        if key not in merged:
            merged[key] = val

    return merged

# ------------------------
# Data Loading
# ------------------------
def load_all_json(base_path, mode="full"):
    all_data = []
    mode = mode.lower()
    assert mode in ["full", "upcoming"], "mode ต้องเป็น 'full' หรือ 'upcoming' เท่านั้น"

    for root, dirs, files in os.walk(base_path):
        target_dir = os.path.join(root, "raw_data", mode)
        print(f"🔍 Looking in: {target_dir}")

        if os.path.exists(target_dir):
            json_files = glob(os.path.join(target_dir, "*.json"))
            print(f"📦 Found {len(json_files)} JSON files")

            for file in json_files:
                print(f"📄 Reading: {file}")
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for d in data:
                                d["source_file"] = file
                                all_data.append(d)
                        else:
                            data["source_file"] = file
                            all_data.append(data)
                except Exception as e:
                    print(f"❌ Error reading {file}: {e}")
        else:
            print(f"🚫 Not found: {target_dir}")
    return all_data

# ------------------------
# 🔍 ลบข้อมูลที่ไม่มี start_date หรือ end_date
# ------------------------
def is_invalid_date(value):
    return value in [None, "", "null", "NULL"]

def filter_valid_events(events):
    return [
        e for e in events
        if not is_invalid_date(e.get("start_date")) and not is_invalid_date(e.get("end_date"))
    ]

def is_invalid_title_or_source(event):
    title = str(event.get("title", "")).strip().lower()
    source_file = str(event.get("source_file", "")).strip().lower()

    invalid_values = {"", "none", "null", "-", "ไม่มีชื่อ", "ไม่มีข้อมูล", "n/a", "ไม่ระบุ"}

    return title in invalid_values or source_file in invalid_values

def filter_clean_events(events):
    """ กรอง event ที่ title และ source_file ต้องไม่เป็นค่าว่างหรือคำไม่สื่อความหมาย """
    return [e for e in events if not is_invalid_title_or_source(e)]

# ------------------------
# Clustering + Merge
# ------------------------
def merge_similar_events(all_events, eps=eps, min_samples=1):
    if not all_events:
        print("⚠️ ไม่มีข้อมูลที่จะ merge")
        return []

    titles = [event.get("title", "") for event in all_events if event.get("title")]
    if not titles:
        print("⚠️ ไม่มี title ให้ clustering")
        return []

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(titles)

    model = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
    labels = model.fit_predict(X)

    clusters = defaultdict(list)
    for idx, label in enumerate(labels):
        clusters[label].append(all_events[idx])

    merged_events = []
    for label, group in clusters.items():
        merged = group[0]
        for other in group[1:]:
            merged = compare_records(merged, other)
        merged["merged_sources"] = list(set(g.get("source_file", "") for g in group))
        merged_events.append(merged)

    return merged_events

# ------------------------
# Run the pipeline
# ------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ โปรดระบุ mode: full หรือ upcoming")
        sys.exit(1)

    mode = sys.argv[1].lower()
    print(f"🚀 เริ่ม Merge Mode: {mode}")

    all_json_data = load_all_json(base_path, mode=mode)
    print(f"📦 โหลดข้อมูลทั้งหมด {len(all_json_data)} รายการจาก '{mode}'")

    valid_json_data = filter_valid_events(all_json_data)
    cleaned_json_data = filter_clean_events(valid_json_data)
    print(f"✅ ข้อมูลหลังกรอง title/source_file: {len(cleaned_json_data)} รายการ")

    merged_data = merge_similar_events(cleaned_json_data)
    print(f"✅ เหลือข้อมูลหลัง merge แล้ว: {len(merged_data)} รายการ")
    # ✅ ทำความสะอาดข้อมูลก่อนเซฟ
    df = pd.DataFrame(merged_data)

    # 1. แก้ categories ที่ว่าง เป็น ["Others"]
    def fix_categories(x):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return ["Others"]
        elif isinstance(x, list):
            return x if len(x) > 0 else ["Others"]
        else:
            return ["Others"]

    df['categories'] = df['categories'].apply(fix_categories)

    # 2. ลบข้อมูลที่ start_date, end_date, location เป็นค่าว่างหรือ 'null', 'none', 'ไม่มีข้อมูล' ฯลฯ
    null_values = {"", "null", "none", "-", "ไม่มีข้อมูล", "ไม่ระบุ", "n/a"}
    for col in ['start_date', 'end_date', 'location']:
        df = df[~df[col].astype(str).str.strip().str.lower().isin(null_values)]

    # 3. ลบข้อมูลที่ status == 'unknown'
    df = df[df['status'] != 'unknown']

    # 4. ลบข้อมูลที่ start_date หรือ end_date รูปแบบไม่ถูกต้อง (ต้องเป็น "22 มกราคม 2025")
    thai_months = {
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    }

    def is_valid_thai_date(date_str):
        if not isinstance(date_str, str):
            return False
        match = re.match(r"^(\d{1,2}) ([ก-๙]+) (\d{4})$", date_str.strip())
        if not match:
            return False
        _, month, year = match.groups()
        if month not in thai_months:
            return False
        try:
            y = int(year)
            return 2020 <= y <= 2100
        except:
            return False

    df = df[df['start_date'].apply(is_valid_thai_date)]
    df = df[df['end_date'].apply(is_valid_thai_date)]
    df['ticket_price'] = df['ticket_price'].apply(lambda x: x if isinstance(x, list) else None)


    # 🧹 สรุปผล
    print(f"🧹 ทำความสะอาดข้อมูลเสร็จสิ้น เหลือ {len(df)} รายการ")

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
    # สร้างโฟลเดอร์ merge_data ข้างๆ merge.py
    output_dir = os.path.join(os.path.dirname(__file__), "merge_data")
    os.makedirs(output_dir, exist_ok=True)
    output_all_path = os.path.join(output_dir, f"merged_{mode}_{timestamp_str}.json")


    # ✅ บันทึก
    with open(output_all_path, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)


    print(f"📁 บันทึกข้อมูลทั้งหมดหลัง merge ที่: {output_all_path}")

# ครั้งแรก (รวม full)
#python merge.py full

# ครั้งถัดไป (รวม upcoming)
#python merge.py upcoming

