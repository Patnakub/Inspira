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
import requests
import time
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


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

thai_month_map = {
    "มกราคม": "01", "กุมภาพันธ์": "02", "มีนาคม": "03", "เมษายน": "04",
    "พฤษภาคม": "05", "มิถุนายน": "06", "กรกฎาคม": "07", "สิงหาคม": "08",
    "กันยายน": "09", "ตุลาคม": "10", "พฤศจิกายน": "11", "ธันวาคม": "12"
}

def parse_thai_date_to_obj(date_str):
    try:
        day, month_thai, year = date_str.strip().split(" ")
        month = thai_month_map.get(month_thai)
        year = int(year)
        if year > 2400:
            year -= 543  # แปลง พ.ศ. เป็น ค.ศ.
        return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
    except Exception:
        return None

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
        print(f" Looking in: {target_dir}")

        if os.path.exists(target_dir):
            json_files = glob(os.path.join(target_dir, "*.json"))
            print(f" Found {len(json_files)} JSON files")

            for file in json_files:
                print(f" Reading: {file}")
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
                    print(f" Error reading {file}: {e}")
        else:
            print(f" Not found: {target_dir}")
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
        print("There is no data to merge.")
        return []

    titles = [event.get("title", "") for event in all_events if event.get("title")]
    if not titles:
        print("No title for clustering")
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
        merged_events.append(merged)

    return merged_events

# ------------------------
# Run the pipeline
# ------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please specify mode with --mode=full or --mode=upcoming.")
        sys.exit(1)

    mode_arg = sys.argv[1]
    if mode_arg.startswith("--mode="):
        mode = mode_arg.split("=")[1].lower()
    else:
        print("Parameter format is invalid. Use --mode=full or --mode=upcoming.")
        sys.exit(1)

    print(f"Merge Mode: {mode}")

    all_json_data = load_all_json(base_path, mode=mode)
    print(f" Load all {len(all_json_data)} items from '{mode}'")

    valid_json_data = filter_valid_events(all_json_data)
    cleaned_json_data = filter_clean_events(valid_json_data)
    print(f"Data after filtering title/source_file: {len(cleaned_json_data)} items")

    merged_data = merge_similar_events(cleaned_json_data)
    print(f"Remaining data after merge: {len(merged_data)} items")
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
        date_str = date_str.replace('\u3000', ' ').strip()  # แก้ full-width space

        # ตรวจจับตัวเลข พ.ศ. และแปลงเป็น ค.ศ. ก่อนส่งเข้า dateparser
        year_match = re.search(r"\b(25\d{2})\b", date_str)
        if year_match:
            buddhist_year = int(year_match.group(1))
            if 2500 <= buddhist_year <= 2600:
                gregorian_year = buddhist_year - 543
                date_str = re.sub(str(buddhist_year), str(gregorian_year), date_str)

        parsed = dateparser.parse(date_str, languages=['th', 'en'])
        if not parsed:
            return False
        return 2020 <= parsed.year <= 2100

    df = df[df['start_date'].apply(is_valid_thai_date)]
    df = df[df['end_date'].apply(is_valid_thai_date)]
    df['ticket_price'] = df['ticket_price'].apply(lambda x: x if isinstance(x, list) else None)
    
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
    # สร้างโฟลเดอร์ merge_data ข้างๆ merge.py
    output_dir = os.path.join(os.path.dirname(__file__), "merge_data")
    os.makedirs(output_dir, exist_ok=True)

    # 🔁 โหลด cache ถ้ามี
    geocode_cache_path = os.path.join(output_dir, "geocode_cache.json")
    if os.path.exists(geocode_cache_path):
        with open(geocode_cache_path, "r", encoding="utf-8") as f:
            geocode_cache = json.load(f)
    else:
        geocode_cache = {}

    # ฟังก์ชันที่ใช้ในการตัดคำที่ไม่จำเป็นออกจาก location
    def normalize_location(location):
        if not isinstance(location, str):
            return location

        location = location.strip()

        # 🔁 กรณีคำว่า "impact" ให้รวมทั้งหมดเป็น "อิมแพ็ค เมืองทองธานี"
        if "impact" in location.lower():
            return "อิมแพ็ค เมืองทองธานี"

        # 🔁 กรณี Paragon Hall ทั้งหมด
        if "paragon hall" in location.lower():
            return "Paragon Hall"

        # 🔁 แมปชื่อเฉพาะที่มักไม่รู้จัก ให้เป็นชื่อสถานที่หลัก
        known_replacements = {
            "Plenary Hall QSNCC": "ศูนย์การประชุมแห่งชาติสิริกิติ์",
            "QSNCC": "ศูนย์การประชุมแห่งชาติสิริกิติ์",
            "BITEC": "ไบเทค บางนา",
            "EH106 ไบเทค บางนา": "ไบเทค บางนา",
            "EH106": "ไบเทค บางนา",
            "ไบเทคฮอลล์": "ไบเทค บางนา",
            "BHIRAJ HALL BITEC": "ไบเทค บางนา",
            "BHIRAJ HALL": "ไบเทค บางนา",
            "Creative Space ชั้น L1 อาคาร D": "TCDC",
            "Creative Space อาคาร D": "TCDC",
            "TCDC อาคาร D": "TCDC",
            "หอศิลปวัฒนธรรมแห่งกรุงเทพมหานคร": "BACC",
            "BACC": "BACC",
            "ริเวอร์ ซิตี้ แบงค็อก": "River City Bangkok",
            "สามย่าน มิตรทาวน์": "Samyan Mitrtown",
            "ซีคอนสแควร์": "Seacon Square",
            "แฟชั่นไอส์แลนด์": "Fashion Island",
            "พารากอน ฮอลล์": "Paragon Hall",
            "ทรู ไอคอน ฮอลล์": "TRUE ICON HALL",
            "อัตตา แกลเลอรี่": "Atta Gallery",
            "แมด - มัน มัน อาร์ต เดสทิเนชั่น": "MAD Art Destination",
            "Xspace": "Xspace Bangkok",
            "Explode Gallery": "Explode Gallery Bangkok",
            "Agni Gallery": "Agni Gallery Bangkok",
            "La Lanta Fine Art": "La Lanta Fine Art Bangkok",
            "HOP - Hub of Photography": "HOP Photo Gallery Bangkok"
        }

        if " - " in location:
            location = location.split(" - ")[0].strip()

        for key, val in known_replacements.items():
            if key in location:
                return val

        # 🧽 ตัดคำที่ไม่จำเป็นด้วย regex
        remove_patterns = [
            r"Hall\s?\d+[-\d]*",              
            r"ไบเทคฮอลล์\s?\d+[-\d]*",        
            r"EH\d+",                         
            r"Plenary Hall",                 
            r"ชั้น\s?[A-Za-z0-9]+",           
            r"ห้อง\s?\d+[-\d]*",              
            r"\bห้องประชุม\b",               
            r"\bสถานที่\b",                  
            r"\bZone\s?[A-Za-z]+\b",         
            r"อาคาร\s?[A-Za-z0-9]+",         
            r"The Portal Lifestyle Complex", 
        ]

        for pattern in remove_patterns:
            location = re.sub(pattern, "", location, flags=re.IGNORECASE)

        location = re.sub(r"\s{2,}", " ", location).strip()

        return location

    GOOGLE_API_KEY = "AIzaSyARUJc-U7xfVvWsV4LnguUoIZQcvoRM2ik"

    def get_lat_lon_from_location_google(location, geocode_cache):
        # ถ้าเจอใน cache แล้ว
        if location in geocode_cache:
            return geocode_cache[location]

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": location,
            "key": GOOGLE_API_KEY
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if data["status"] == "OK":
                result = data["results"][0]["geometry"]["location"]
                lat, lon = result["lat"], result["lng"]
                geocode_cache[location] = {"lat": lat, "lon": lon}
                time.sleep(0.3)  # ปลอดภัยกว่ากับหลายรายการ
                return {"lat": lat, "lon": lon}
            else:
                print(f"[Google] No coordinates found for '{location}' | Status: {data['status']}")
        except Exception as e:
            print(f"[Google] An error occurred with '{location}': {e}")

        # ถ้าไม่เจอให้เก็บเป็น None
        geocode_cache[location] = None
        return None
    
    def get_lat_lon_from_places_api(location, geocode_cache):
        if location in geocode_cache:
            return geocode_cache[location]

        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": location,
            "key": GOOGLE_API_KEY
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if data["status"] == "OK" and len(data["results"]) > 0:
                place = data["results"][0]
                lat = place["geometry"]["location"]["lat"]
                lon = place["geometry"]["location"]["lng"]
                geocode_cache[location] = {"lat": lat, "lon": lon}
                time.sleep(0.3)
                return {"lat": lat, "lon": lon}
            else:
                print(f"[Places API] No coordinates found for '{location}' | Status: {data['status']}")
        except Exception as e:
            print(f"[Places API] Error with '{location}': {e}")

        geocode_cache[location] = None
        return None

    
    def get_lat_lon_from_location_nominatim(location, geocode_cache):
        if location in geocode_cache:
            return geocode_cache[location]
        
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": location,
            "format": "json",
            "limit": 1
        }
        headers = {
            "User-Agent": "ExhibitionProject/1.0 (your_email@example.com)"
        }
        try:
            response = requests.get(url, params=params, headers=headers)
            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                geocode_cache[location] = {"lat": lat, "lon": lon}
                time.sleep(1)
                return {"lat": lat, "lon": lon}
        except Exception as e:
            print(f"[Nominatim] An error occurred with '{location}': {e}")
        
        geocode_cache[location] = None
        return None

    def get_lat_lon_with_fallback(location, geocode_cache):
        normalized_location = normalize_location(location)

        result = get_lat_lon_from_location_google(normalized_location, geocode_cache)
        if result:
            return result

        result = get_lat_lon_from_places_api(normalized_location, geocode_cache)
        if result:
            return result

        result = get_lat_lon_from_location_nominatim(normalized_location, geocode_cache)
        if result:
            return result

        return None



    # เพิ่มพิกัดใน DataFrame
    df["latitude"] = None
    df["longitude"] = None

    not_found_locations = []

    for idx, row in df.iterrows():
        loc = row.get("location")
        if isinstance(loc, str) and loc.strip():
            result = get_lat_lon_with_fallback(loc.strip(), geocode_cache)
            if result:
                df.at[idx, "latitude"] = result["lat"]
                df.at[idx, "longitude"] = result["lon"]
            else:
                not_found_locations.append(loc.strip())

    # 🔐 บันทึก cache เก็บไว้ใช้รอบหน้า
    with open(geocode_cache_path, "w", encoding="utf-8") as f:
        json.dump(geocode_cache, f, ensure_ascii=False, indent=2)

    # 🧹 สรุปผล
    print(f"Data cleaning completed, leaving {len(df)} items.")

    output_all_path = os.path.join(output_dir, f"merged_{mode}_{timestamp_str}.json")

    missing_count = df["latitude"].isnull().sum()

    # ตั้งค่า category_verified = False หากยังไม่มี
    if 'category_verified' not in df.columns:
        df['category_verified'] = False
    else:
        df['category_verified'] = df['category_verified'].fillna(False)
    
    # 1. เวอร์ชันสำหรับ MongoDB → datetime object จริง
    df["start_date_obj"] = df["start_date"].apply(parse_thai_date_to_obj)
    df["end_date_obj"] = df["end_date"].apply(parse_thai_date_to_obj)

    # 2. สร้างสำเนาไว้ export → แปลง datetime เป็น string
    df_export = df.copy()
    df_export["start_date_obj"] = df_export["start_date_obj"].apply(lambda x: x.isoformat() if pd.notnull(x) else None)
    df_export["end_date_obj"] = df_export["end_date_obj"].apply(lambda x: x.isoformat() if pd.notnull(x) else None)

    # 3. บันทึกไฟล์ JSON เดียวเหมือนเดิม
    with open(output_all_path, "w", encoding="utf-8") as f:
        json.dump(df_export.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
        print(f"Save all data after merge to: {output_all_path}")

# ครั้งแรก (รวม full)
# python merge.py --mode=full

# ครั้งถัดไป (รวม upcoming)
# python merge.py --mode=upcoming

