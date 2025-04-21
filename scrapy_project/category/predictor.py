"""
import pandas as pd
import numpy as np
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ===== 1. โหลดข้อมูล และเทรนโมเดล =====
df = pd.read_csv('data_example.csv')  # ต้องมี title, description, category
df['text'] = df['title'] + " " + df['description']
X_train, X_test, y_train, y_test = train_test_split(df['text'], df['category'], test_size=0.2, random_state=42)

model = make_pipeline(
    TfidfVectorizer(max_features=3000, ngram_range=(1, 2)),
    LinearSVC()
)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# ===== 2. Keyword Dictionary =====
keyword_dict = {
    "Art & Design": [
        "art", "gallery", "exhibition", "painting", "drawing", "sculpture", "illustration", "installation",
        "creative", "visual", "fine art", "artist", "design", "graphic", "interior design", "product design",
        "architecture", "aesthetic", "contemporary art", "modern art", "ศิลปะ", "นิทรรศการ", "จิตรกรรม",
        "ภาพวาด", "ประติมากรรม", "ออกแบบ", "ออกแบบกราฟิก", "มัณฑนศิลป์", "สร้างสรรค์", "ภาพถ่าย",
        "แฟชั่นอาร์ต", "ศิลปิน", "ผลงานศิลปะ", "สถาปัตยกรรม", "ดีไซน์", "ทัศนศิลป์", "กราฟิกดีไซน์",
        "วาดภาพ", "แสดงผลงาน", "นิทรรศการศิลปะ", "หอศิลป์", "จัดแสดงผลงาน", "ศิลปะร่วมสมัย",
        "งานฝีมือ", "ศิลปะดิจิทัล", "งานออกแบบ", "งานศิลป์", "ตกแต่งภายใน", "จัดวางศิลป์", "โชว์เคส"
    ],
    "Beauty & Fashion": [
        "fashion", "beauty", "cosmetic", "makeup", "skincare", "model", "clothing", "style", "runway",
        "hairstyle", "nail", "accessory", "jewelry", "wardrobe", "catwalk", "couture", "trend", "grooming",
        "แฟชั่น", "ความงาม", "เครื่องสำอาง", "แต่งหน้า", "ดูแลผิว", "นางแบบ", "เสื้อผ้า", "สไตล์",
        "ทรงผม", "ทำผม", "ทำเล็บ", "เครื่องประดับ", "โชว์แฟชั่น", "เดินแบบ", "เทรนด์", "ดีไซน์เนอร์",
        "เสื้อผ้าแฟชั่น", "แฟชั่นโชว์", "งานแฟชั่น", "ดูแลตัวเอง", "แฟชั่นดีไซน์", "เครื่องแต่งกาย",
        "แฟชั่นเสื้อผ้า", "ความงามและสุขภาพ", "บิวตี้", "ลุค", "แบรนด์เนม", "แฟชั่นเครื่องประดับ",
        "สไตลิสต์", "อุตสาหกรรมแฟชั่น", "เสื้อผ้าดีไซน์"
    ],
    "Home & Furniture": [
        "home", "furniture", "decor", "interior", "living", "sofa", "kitchen", "bedroom", "bathroom",
        "woodwork", "lighting", "carpet", "homeware", "renovation", "home improvement", "appliance",
        "smart home", "บ้าน", "เฟอร์นิเจอร์", "ตกแต่งบ้าน", "ตกแต่งภายใน", "ห้องนั่งเล่น", "ห้องครัว",
        "ห้องนอน", "ห้องน้ำ", "เครื่องใช้ไฟฟ้า", "ของแต่งบ้าน", "งานไม้", "ผ้าม่าน", "โคมไฟ", "ชั้นวาง",
        "เบาะ", "เตียง", "โต๊ะ", "โซฟา", "เก้าอี้", "รีโนเวท", "ปรับปรุงบ้าน", "เครื่องเรือน", "ห้องรับแขก",
        "ตู้เสื้อผ้า", "ตกแต่งสไตล์", "วัสดุตกแต่ง", "งานอินทีเรีย", "ของใช้ในบ้าน", "บ้านอัจฉริยะ",
        "สไตล์บ้าน", "บ้านโมเดิร์น", "อุปกรณ์ตกแต่ง"
    ],
    "Business": [
        "business", "startup", "entrepreneur", "corporate", "investment", "finance", "economy", "marketing",
        "management", "strategy", "networking", "ecommerce", "sales", "pitch", "venture", "commerce",
        "retail", "ธุรกิจ", "สตาร์ทอัพ", "ผู้ประกอบการ", "การเงิน", "การลงทุน", "เศรษฐกิจ", "การตลาด",
        "กลยุทธ์", "บริหาร", "การจัดการ", "สัมมนาธุรกิจ", "เจรจาธุรกิจ", "การค้า", "งานขาย",
        "ธุรกิจออนไลน์", "ค้าปลีก", "วางแผนธุรกิจ", "กิจการ", "องค์กร", "พนักงาน", "เจ้าของกิจการ",
        "โมเดลธุรกิจ", "กำไร", "หุ้น", "ธุรกิจใหม่", "นักธุรกิจ", "ฝึกอบรมธุรกิจ", "เงินทุน",
        "พัฒนาองค์กร", "แนวคิดธุรกิจ"
    ],
    "Education": [
        "education", "learning", "university", "school", "academic", "student", "study", "research",
        "seminar", "lecture", "workshop", "training", "conference", "tutor", "exam", "curriculum",
        "knowledge", "การศึกษา", "เรียนรู้", "มหาวิทยาลัย", "โรงเรียน", "นักเรียน", "นักศึกษา",
        "วิชาการ", "งานวิจัย", "อบรม", "สัมมนา", "บรรยาย", "ติว", "สอบ", "หลักสูตร", "ห้องเรียน",
        "ฝึกอบรม", "การเรียน", "ครู", "อาจารย์", "แนะแนว", "สื่อการสอน", "เทคนิคการสอน",
        "สถาบัน", "การสอน", "ความรู้", "กิจกรรมการเรียนรู้", "การพัฒนา", "ฝึกทักษะ", "ชั้นเรียน",
        "การสื่อสารในห้องเรียน"
    ],
    "Concert": [
        "concert", "music", "live", "band", "performance", "gig", "show",
        "singer", "dj", "orchestra", "festival", "sound", "song", "musician",
        "tour", "setlist", "stage", "ดนตรี", "คอนเสิร์ต", "แสดงสด", "วงดนตรี",
        "ศิลปิน", "ร้องเพลง", "ดีเจ", "นักร้อง", "เวที", "เครื่องเสียง",
        "เพลง", "โชว์", "งานดนตรี", "มหกรรมดนตรี", "เทศกาลเพลง", "มิวสิค",
        "นักดนตรี", "แสดงคอนเสิร์ต", "เปิดการแสดง", "เต้น", "เล่นสด",
        "แสดงบนเวที", "บัตรคอนเสิร์ต", "รายการเพลง", "งานแสดง", "เสียงเพลง",
        "ศิลปินดัง", "ร็อค", "ป็อป", "แจ๊ส", "ไลฟ์โชว์", "มิวสิคเฟสติวัล"
    ],
    "Technology": [
        "tech", "technology", "robot", "ai", "iot", "software", "hardware",
        "programming", "coding", "machine learning", "data", "cyber",
        "blockchain", "cloud", "innovation", "smart", "electronics", "drone",
        "vr", "ar", "mobile", "app", "application", "developer", "smartphone",
        "เทคโนโลยี", "หุ่นยนต์", "ปัญญาประดิษฐ์", "อินเทอร์เน็ตของสรรพสิ่ง",
        "ซอฟต์แวร์", "ฮาร์ดแวร์", "เขียนโปรแกรม", "ข้อมูล", "ระบบอัจฉริยะ",
        "เครื่องอิเล็กทรอนิกส์", "แอป", "แอปพลิเคชัน", "มือถือ", "สมาร์ทโฟน",
        "เทคโนโลยีใหม่", "พัฒนาซอฟต์แวร์", "นวัตกรรม", "โลกดิจิทัล",
        "ความปลอดภัยไซเบอร์", "ระบบคลาวด์", "อุปกรณ์ไฮเทค", "วิศวกรรมซอฟต์แวร์",
        "เทคโนโลยีสารสนเทศ", "บล็อกเชน"

    ],
    "Book": [
        "book", "literature", "novel", "author", "library", "publishing",
        "story", "reading", "poetry", "fiction", "non-fiction", "writing",
        "biography", "comic", "manga", "bestseller", "literary",
        "หนังสือ", "วรรณกรรม", "นวนิยาย", "ผู้เขียน", "ห้องสมุด", "สำนักพิมพ์",
        "เรื่องเล่า", "อ่านหนังสือ", "บทกวี", "เรื่องแต่ง", "สารคดี", "เขียนหนังสือ",
        "นักเขียน", "ชีวประวัติ", "การอ่าน", "หนังสือขายดี", "วรรณคดี", "นิยายภาพ",
        "หนังสือเด็ก", "เล่มโปรด", "หนังสือการ์ตูน", "งานวรรณกรรม", "งานหนังสือ",
        "งานเขียน", "หนังสือวาด", "การตีพิมพ์", "งานอ่าน", "เรื่องสั้น", "หนังสือเสียง"

    ],
    "Food & Drink": [
        "food", "drink", "beverage", "cuisine", "dining", "restaurant", "cooking",
        "chef", "recipe", "snack", "bar", "alcohol", "coffee", "tea", "wine",
        "beer", "taste", "flavor", "bake", "meal", "culinary", "festival", "menu",
        "อาหาร", "เครื่องดื่ม", "ของกิน", "การกิน", "ร้านอาหาร", "ร้านกาแฟ",
        "ชงกาแฟ", "ปรุงอาหาร", "เชฟ", "สูตรอาหาร", "ของว่าง", "งานอาหาร",
        "เบเกอรี่", "ขนม", "เครื่องดื่มแอลกอฮอล์", "เบียร์", "ไวน์", "ชา", "กาแฟ",
        "ชิมอาหาร", "รสชาติ", "งานชิม", "บุฟเฟ่ต์", "งานเครื่องดื่ม", "การทำอาหาร",
        "ร้านขนม", "งานเฟสติวัลอาหาร"
    ]
}

# ===== 3. Class labels =====
class_labels = model.named_steps['linearsvc'].classes_

# ===== 4. ฟังก์ชันทำนายแบบ Hybrid (TF-IDF + Keyword) =====
def predict_category(title, description, score_diff_threshold=0.3):
    text = title + " " + description
    X_input = model.named_steps['tfidfvectorizer'].transform([text])
    scores = model.named_steps['linearsvc'].decision_function(X_input)

    top_indices = np.argsort(scores[0])[::-1]
    top1 = class_labels[top_indices[0]]
    top2 = class_labels[top_indices[1]]
    top1_score = scores[0][top_indices[0]]
    top2_score = scores[0][top_indices[1]]

    matched_keyword_categories = []
    for cat, keywords in keyword_dict.items():
        if any(kw.lower() in text.lower() for kw in keywords):
            matched_keyword_categories.append(cat)

    if top2 not in matched_keyword_categories and abs(top1_score - top2_score) > score_diff_threshold:
        return [top1]
    else:
        return [top1, top2]

# ===== 5. บันทึกโมเดลเพื่อใช้ในระบบอื่น =====
joblib.dump(model, os.path.join(os.path.dirname(__file__), "category_model.joblib"))

"""
import pandas as pd
import numpy as np
import joblib

import os
model_path = os.path.join(os.path.dirname(__file__), "category_model.joblib")
model = joblib.load(model_path)


keyword_dict = {
    "Art & Design": [
        "art", "gallery", "exhibition", "painting", "drawing", "sculpture", "illustration", "installation",
        "creative", "visual", "fine art", "artist", "design", "graphic", "interior design", "product design",
        "architecture", "aesthetic", "contemporary art", "modern art", "ศิลปะ", "นิทรรศการ", "จิตรกรรม",
        "ภาพวาด", "ประติมากรรม", "ออกแบบ", "ออกแบบกราฟิก", "มัณฑนศิลป์", "สร้างสรรค์", "ภาพถ่าย",
        "แฟชั่นอาร์ต", "ศิลปิน", "ผลงานศิลปะ", "สถาปัตยกรรม", "ดีไซน์", "ทัศนศิลป์", "กราฟิกดีไซน์",
        "วาดภาพ", "แสดงผลงาน", "นิทรรศการศิลปะ", "หอศิลป์", "จัดแสดงผลงาน", "ศิลปะร่วมสมัย",
        "งานฝีมือ", "ศิลปะดิจิทัล", "งานออกแบบ", "งานศิลป์", "ตกแต่งภายใน", "จัดวางศิลป์", "โชว์เคส"
    ],
    "Beauty & Fashion": [
        "fashion", "beauty", "cosmetic", "makeup", "skincare", "model", "clothing", "style", "runway",
        "hairstyle", "nail", "accessory", "jewelry", "wardrobe", "catwalk", "couture", "trend", "grooming",
        "แฟชั่น", "ความงาม", "เครื่องสำอาง", "แต่งหน้า", "ดูแลผิว", "นางแบบ", "เสื้อผ้า", "สไตล์",
        "ทรงผม", "ทำผม", "ทำเล็บ", "เครื่องประดับ", "โชว์แฟชั่น", "เดินแบบ", "เทรนด์", "ดีไซน์เนอร์",
        "เสื้อผ้าแฟชั่น", "แฟชั่นโชว์", "งานแฟชั่น", "ดูแลตัวเอง", "แฟชั่นดีไซน์", "เครื่องแต่งกาย",
        "แฟชั่นเสื้อผ้า", "ความงามและสุขภาพ", "บิวตี้", "ลุค", "แบรนด์เนม", "แฟชั่นเครื่องประดับ",
        "สไตลิสต์", "อุตสาหกรรมแฟชั่น", "เสื้อผ้าดีไซน์"
    ],
    "Home & Furniture": [
        "home", "furniture", "decor", "interior", "living", "sofa", "kitchen", "bedroom", "bathroom",
        "woodwork", "lighting", "carpet", "homeware", "renovation", "home improvement", "appliance",
        "smart home", "บ้าน", "เฟอร์นิเจอร์", "ตกแต่งบ้าน", "ตกแต่งภายใน", "ห้องนั่งเล่น", "ห้องครัว",
        "ห้องนอน", "ห้องน้ำ", "เครื่องใช้ไฟฟ้า", "ของแต่งบ้าน", "งานไม้", "ผ้าม่าน", "โคมไฟ", "ชั้นวาง",
        "เบาะ", "เตียง", "โต๊ะ", "โซฟา", "เก้าอี้", "รีโนเวท", "ปรับปรุงบ้าน", "เครื่องเรือน", "ห้องรับแขก",
        "ตู้เสื้อผ้า", "ตกแต่งสไตล์", "วัสดุตกแต่ง", "งานอินทีเรีย", "ของใช้ในบ้าน", "บ้านอัจฉริยะ",
        "สไตล์บ้าน", "บ้านโมเดิร์น", "อุปกรณ์ตกแต่ง"
    ],
    "Business": [
        "business", "startup", "entrepreneur", "corporate", "investment", "finance", "economy", "marketing",
        "management", "strategy", "networking", "ecommerce", "sales", "pitch", "venture", "commerce",
        "retail", "ธุรกิจ", "สตาร์ทอัพ", "ผู้ประกอบการ", "การเงิน", "การลงทุน", "เศรษฐกิจ", "การตลาด",
        "กลยุทธ์", "บริหาร", "การจัดการ", "สัมมนาธุรกิจ", "เจรจาธุรกิจ", "การค้า", "งานขาย",
        "ธุรกิจออนไลน์", "ค้าปลีก", "วางแผนธุรกิจ", "กิจการ", "องค์กร", "พนักงาน", "เจ้าของกิจการ",
        "โมเดลธุรกิจ", "กำไร", "หุ้น", "ธุรกิจใหม่", "นักธุรกิจ", "ฝึกอบรมธุรกิจ", "เงินทุน",
        "พัฒนาองค์กร", "แนวคิดธุรกิจ"
    ],
    "Education": [
        "education", "learning", "university", "school", "academic", "student", "study", "research",
        "seminar", "lecture", "workshop", "training", "conference", "tutor", "exam", "curriculum",
        "knowledge", "การศึกษา", "เรียนรู้", "มหาวิทยาลัย", "โรงเรียน", "นักเรียน", "นักศึกษา",
        "วิชาการ", "งานวิจัย", "อบรม", "สัมมนา", "บรรยาย", "ติว", "สอบ", "หลักสูตร", "ห้องเรียน",
        "ฝึกอบรม", "การเรียน", "ครู", "อาจารย์", "แนะแนว", "สื่อการสอน", "เทคนิคการสอน",
        "สถาบัน", "การสอน", "ความรู้", "กิจกรรมการเรียนรู้", "การพัฒนา", "ฝึกทักษะ", "ชั้นเรียน",
        "การสื่อสารในห้องเรียน"
    ],
    "Concert": [
        "concert", "music", "live", "band", "performance", "gig", "show",
        "singer", "dj", "orchestra", "festival", "sound", "song", "musician",
        "tour", "setlist", "stage", "ดนตรี", "คอนเสิร์ต", "แสดงสด", "วงดนตรี",
        "ศิลปิน", "ร้องเพลง", "ดีเจ", "นักร้อง", "เวที", "เครื่องเสียง",
        "เพลง", "โชว์", "งานดนตรี", "มหกรรมดนตรี", "เทศกาลเพลง", "มิวสิค",
        "นักดนตรี", "แสดงคอนเสิร์ต", "เปิดการแสดง", "เต้น", "เล่นสด",
        "แสดงบนเวที", "บัตรคอนเสิร์ต", "รายการเพลง", "งานแสดง", "เสียงเพลง",
        "ศิลปินดัง", "ร็อค", "ป็อป", "แจ๊ส", "ไลฟ์โชว์", "มิวสิคเฟสติวัล"
    ],
    "Technology": [
        "tech", "technology", "robot", "ai", "iot", "software", "hardware",
        "programming", "coding", "machine learning", "data", "cyber",
        "blockchain", "cloud", "innovation", "smart", "electronics", "drone",
        "vr", "ar", "mobile", "app", "application", "developer", "smartphone",
        "เทคโนโลยี", "หุ่นยนต์", "ปัญญาประดิษฐ์", "อินเทอร์เน็ตของสรรพสิ่ง",
        "ซอฟต์แวร์", "ฮาร์ดแวร์", "เขียนโปรแกรม", "ข้อมูล", "ระบบอัจฉริยะ",
        "เครื่องอิเล็กทรอนิกส์", "แอป", "แอปพลิเคชัน", "มือถือ", "สมาร์ทโฟน",
        "เทคโนโลยีใหม่", "พัฒนาซอฟต์แวร์", "นวัตกรรม", "โลกดิจิทัล",
        "ความปลอดภัยไซเบอร์", "ระบบคลาวด์", "อุปกรณ์ไฮเทค", "วิศวกรรมซอฟต์แวร์",
        "เทคโนโลยีสารสนเทศ", "บล็อกเชน"

    ],
    "Book": [
        "book", "literature", "novel", "author", "library", "publishing",
        "story", "reading", "poetry", "fiction", "non-fiction", "writing",
        "biography", "comic", "manga", "bestseller", "literary",
        "หนังสือ", "วรรณกรรม", "นวนิยาย", "ผู้เขียน", "ห้องสมุด", "สำนักพิมพ์",
        "เรื่องเล่า", "อ่านหนังสือ", "บทกวี", "เรื่องแต่ง", "สารคดี", "เขียนหนังสือ",
        "นักเขียน", "ชีวประวัติ", "การอ่าน", "หนังสือขายดี", "วรรณคดี", "นิยายภาพ",
        "หนังสือเด็ก", "เล่มโปรด", "หนังสือการ์ตูน", "งานวรรณกรรม", "งานหนังสือ",
        "งานเขียน", "หนังสือวาด", "การตีพิมพ์", "งานอ่าน", "เรื่องสั้น", "หนังสือเสียง"

    ],
    "Food & Drink": [
        "food", "drink", "beverage", "cuisine", "dining", "restaurant", "cooking",
        "chef", "recipe", "snack", "bar", "alcohol", "coffee", "tea", "wine",
        "beer", "taste", "flavor", "bake", "meal", "culinary", "festival", "menu",
        "อาหาร", "เครื่องดื่ม", "ของกิน", "การกิน", "ร้านอาหาร", "ร้านกาแฟ",
        "ชงกาแฟ", "ปรุงอาหาร", "เชฟ", "สูตรอาหาร", "ของว่าง", "งานอาหาร",
        "เบเกอรี่", "ขนม", "เครื่องดื่มแอลกอฮอล์", "เบียร์", "ไวน์", "ชา", "กาแฟ",
        "ชิมอาหาร", "รสชาติ", "งานชิม", "บุฟเฟ่ต์", "งานเครื่องดื่ม", "การทำอาหาร",
        "ร้านขนม", "งานเฟสติวัลอาหาร"
    ]
}

class_labels = model.named_steps['linearsvc'].classes_

def predict_category(title, description, score_diff_threshold=0.3):
    text = title + " " + description
    X_input = model.named_steps['tfidfvectorizer'].transform([text])
    scores = model.named_steps['linearsvc'].decision_function(X_input)

    top_indices = np.argsort(scores[0])[::-1]
    top1 = class_labels[top_indices[0]]
    top2 = class_labels[top_indices[1]]
    top1_score = scores[0][top_indices[0]]
    top2_score = scores[0][top_indices[1]]

    matched_keyword_categories = []
    for cat, keywords in keyword_dict.items():
        if any(kw.lower() in text.lower() for kw in keywords):
            matched_keyword_categories.append(cat)

    if top2 not in matched_keyword_categories and abs(top1_score - top2_score) > score_diff_threshold:
        return [top1]
    else:
        return [top1, top2]
