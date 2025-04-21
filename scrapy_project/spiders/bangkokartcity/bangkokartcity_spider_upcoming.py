import scrapy
import re
import json
import os
import datetime
from scrapy_project.category.predictor import predict_category
import dateparser
import html

class BangkokArtSpider(scrapy.Spider):
    name = "bangkokartcity_spider_upcoming"
    allowed_domains = ["bangkokartcity.org"]
    start_urls = ["https://www.bangkokartcity.org/th/discover"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.past_event_count = 0  # ✅ ตัวแปรนับจำนวน past event

    def parse(self, response):
        # ดึงลิงก์ของแต่ละนิทรรศการ
        exhibition_links = response.css("a.framer-vtg5wl.framer-1xv5ffg::attr(href)").getall()
        
        for link in exhibition_links:
            full_url = response.urljoin(link)
            yield scrapy.Request(full_url, callback=self.parse_exhibition)

    def parse_exhibition(self, response):
        title = response.css("h1.framer-text::text").get()
        description = " ".join(response.css("div.framer-129oip7 p.framer-text::text").getall()).strip()

        date_text = response.css("div.framer-u6f86y p.framer-text::text").get()
        start_date, end_date = self.extract_dates(date_text)

        event_slot_time_raw = response.css("div.framer-1xu6drh p.framer-text::text").get()
        event_slot_time = self.extract_time(event_slot_time_raw)

        location = response.css("div.framer-1mowxnk p.framer-text::text").get()

        status = determine_status(start_date, end_date)
        if status not in ["upcoming", "ongoing"]:
            self.past_event_count += 1
            if self.past_event_count > 30:
                self.log("🛑 เจอ past event เกิน 30 รายการ — หยุดทำงาน")
                raise scrapy.exceptions.CloseSpider("Too many past events")
            return

        cover_picture = response.css("img[decoding='async']::attr(srcset)").get()
        if cover_picture:
            cover_picture = cover_picture.split(",")[-1].split(" ")[0]

        ticket, ticket_price = self.extract_ticket_info(description)

        if not title:
            self.logger.warning(f"Title not found for {response.url}")
            title = None

        reliability_score = 2
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        predicted_categories = predict_category(title, description)

        data = {
            "title": title.strip() if title else "null",
            "description": description if description else "No description",
            "start_date": start_date,
            "end_date": end_date,
            "categories": predicted_categories,
            "event_slot_time": event_slot_time if event_slot_time else "ไม่ระบุ",
            "location": location.strip() if location else "ไม่ระบุ",
            "url": response.url,
            "ticket": ticket,
            "ticket_price": ticket_price,
            "cover_picture": cover_picture if cover_picture else "No cover picture",
            "reliability_score": reliability_score,
            "timestamp": timestamp,
            "status": determine_status(start_date, end_date)

        }

        # ตรวจสอบก่อนบันทึกไฟล์
        if not data:
            self.logger.warning(f"No data extracted for {response.url}")
            return
        
         # กำหนดชื่อไฟล์
        filename = re.sub(r"[\\/:*?\"<>|]", "_", title) + ".json"

        # หาตำแหน่งโฟลเดอร์ของ spider แล้วต่อด้วย raw_data
        base_dir = os.path.dirname(os.path.abspath(__file__))
        raw_data_dir = os.path.join(base_dir, "raw_data", "upcoming")
        os.makedirs(raw_data_dir, exist_ok=True)  # สร้างโฟลเดอร์ถ้ายังไม่มี

        filepath = os.path.join(raw_data_dir, filename)

        # เขียนไฟล์ JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        yield data
    
    def extract_dates(self, text):
        """ ฟังก์ชันดึงวันที่จากข้อความ และแปลงปี พ.ศ. เป็น ค.ศ. """
        months = {
            "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
            "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12
        }

        pattern = r"(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})\s*-\s*(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})"
        match = re.search(pattern, text)

        if match:
            start_day, start_month, start_year, end_day, end_month, end_year = match.groups()
            # แปลง พ.ศ. → ค.ศ.
            start_year = int(start_year) - 543
            end_year = int(end_year) - 543

            start_date = f"{int(start_day)} {start_month} {start_year}"
            end_date = f"{int(end_day)} {end_month} {end_year}"
            return start_date, end_date

        return "ไม่ระบุ", "ไม่ระบุ"

    
    def extract_time(self, text):
        """ ฟังก์ชันดึงเฉพาะช่วงเวลา 10:00-17:00 """
        match = re.search(r"(\d{1,2}:\d{2}-\d{1,2}:\d{2})", text)
        return match.group(1) if match else "ไม่ระบุ"

    def extract_ticket_info(self, description_text):
        ticket_keywords = ["บัตร", "ticket"]
        price_keywords = [
            "บัตรราคา", "ราคาบัตร", "ค่าเข้าชม", "ticket price", "price",
            "entry fee", "admission", "entry ticket", "ticket fee"
        ]
        free_keywords = [
            "ฟรี", "free", "บัตรฟรี", "เข้าฟรี", "ไม่มีค่าใช้จ่าย",
            "no charge", "free entry", "free admission"
        ]
        exclude_keywords = ["ค่าธรรมเนียม", "service charge", "ค่าบริการ", "surcharge"]
        skip_prices = {"67", "68", "23", "24", "25", "100"}

        clean_text = html.unescape(description_text)
        full_text = clean_text.lower()
        paragraphs = re.split(r"[.\n\r]", clean_text)

        ticket = "ไม่มีค่าเข้าชม"
        raw_prices = []

        if any(free in full_text for free in free_keywords):
            return "ไม่มีค่าเข้าชม", None

        if any(keyword in full_text for keyword in ticket_keywords):
            ticket = "มีค่าเข้าชม"

        for p in paragraphs:
            p_clean = re.sub(r"<.*?>", "", p)
            lower_p = p_clean.lower()

            if any(ex_kw in lower_p for ex_kw in exclude_keywords):
                continue

            if any(price_kw in lower_p for price_kw in price_keywords) or "บาท" in lower_p:
                matches = re.findall(r"\d{1,3}(?:,\d{3})+|\d{3,5}", lower_p)
                for m in matches:
                    try:
                        price = int(m.replace(",", ""))
                        if str(price) in skip_prices or re.match(r"^(25|20)\d{2}$", str(price)):
                            continue
                        if price >= 32:
                            raw_prices.append(price)
                    except:
                        continue

        filtered_prices = raw_prices
        if len(raw_prices) >= 2:
            max_price = max(raw_prices)
            threshold = max_price * 0.3
            filtered_prices = [p for p in raw_prices if p >= threshold]

        if ticket == "ไม่มีค่าเข้าชม" and filtered_prices:
            ticket = "มีค่าเข้าชม"

        return ticket, sorted(filtered_prices) if filtered_prices else None
    
def determine_status(start_date, end_date):
    today = datetime.date.today()
    start = dateparser.parse(start_date, languages=["th", "en"])
    end = dateparser.parse(end_date, languages=["th", "en"])

    if not start or not end:
        return "unknown"

    if today < start.date():
        return "upcoming"
    elif start.date() <= today <= end.date():
        return "ongoing"
    else:
        return "past"


