import scrapy
import re
import json
import os
import datetime
from scrapy_project.category.predictor import predict_category
import dateparser
import html 

class ImpactEventSpider(scrapy.Spider):
    name = "impact_spider_upcoming"
    allowed_domains = ["impact.co.th"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.current_year = 2025
        self.current_month = 3
        self.current_page = 1
        self.empty_month_count = 0

    def start_requests(self):
        url = self.build_url(self.current_year, self.current_month, self.current_page)
        yield scrapy.Request(url=url, callback=self.parse)

    def build_url(self, year, month, page):
        return f"https://www.impact.co.th/index.php/visitor/event/th/all/{month:02d}/{year}/{page}"
    
    def parse(self, response):
        event_links = response.css("div.box-content span.event-name a::attr(href)").getall()

        if event_links:
            self.empty_month_count = 0  # reset ถ้ามีข้อมูล
            for link in event_links:
                yield response.follow(link, self.parse_event)

            # ไปหน้าถัดไปของเดือนเดียวกัน
            self.current_page += 1
            next_url = self.build_url(self.current_year, self.current_month, self.current_page)
            yield scrapy.Request(url=next_url, callback=self.parse)

        else:
            # ถ้าไม่มี event ในหน้านั้น → ข้ามไปเดือนถัดไป
            self.empty_month_count += 1
            self.current_page = 1
            self.current_month += 1

            if self.current_month > 12:
                self.current_month = 1
                self.current_year += 1

            if self.empty_month_count >= 10:
                self.logger.info("No data for 10 consecutive months. Stopping spider.")
                return

            next_url = self.build_url(self.current_year, self.current_month, self.current_page)
            yield scrapy.Request(url=next_url, callback=self.parse)

    def parse_event(self, response):
        title = response.css("div.box-head::text").get(default="null").strip()
        start_date, end_date, event_slot_time, location = self.extract_event_details(response)
        description, event_url = self.extract_description_and_url(response)

        if event_slot_time == "Several Time":
            event_slot_time = self.extract_time_from_description(description)

        ticket, ticket_price = self.extract_ticket_info(description)
        cover_picture = response.css("img.event-banner::attr(src)").get()
        if cover_picture and not cover_picture.startswith("http"):
            cover_picture = f"https://www.impact.co.th{cover_picture}"
        cover_picture = cover_picture if cover_picture else "null"

        status = determine_status(start_date, end_date)
        if status not in ["upcoming", "ongoing"]:
            self.past_event_count += 1
            if self.past_event_count > 60:
                self.log("🛑 เจอ past event เกิน 60 รายการ — หยุดทำงาน")
                raise scrapy.exceptions.CloseSpider("Too many past events")
            return

        predicted_categories = predict_category(title, description)
        reliability_score = 5
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        event_data = {
            "title": title if title else "null",
            "description": description if description else "null",
            "categories": predicted_categories,
            "start_date": start_date,
            "end_date": end_date,
            "event_slot_time": event_slot_time,
            "location": f"Impact {location}" if location != "null" else "null",
            "url": event_url,
            "ticket": ticket,
            "ticket_price": ticket_price,
            "cover_picture": cover_picture,
            "reliability_score": reliability_score,
            "timestamp": timestamp,
            "status": determine_status(start_date, end_date)
        }

         # กำหนดชื่อไฟล์
        filename = re.sub(r"[\\/:*?\"<>|]", "_", title) + ".json"

        # หาตำแหน่งโฟลเดอร์ของ spider แล้วต่อด้วย raw_data
        base_dir = os.path.dirname(os.path.abspath(__file__))
        raw_data_dir = os.path.join(base_dir, "raw_data", "upcoming")
        os.makedirs(raw_data_dir, exist_ok=True)  # สร้างโฟลเดอร์ถ้ายังไม่มี

        filepath = os.path.join(raw_data_dir, filename)

        # เขียนไฟล์ JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(event_data, f, ensure_ascii=False, indent=4)

        yield event_data

    def extract_event_details(self, response):
        month_map = {
            "January": "มกราคม", "February": "กุมภาพันธ์", "March": "มีนาคม", "April": "เมษายน",
            "May": "พฤษภาคม", "June": "มิถุนายน", "July": "กรกฎาคม", "August": "สิงหาคม",
            "September": "กันยายน", "October": "ตุลาคม", "November": "พฤศจิกายน", "December": "ธันวาคม"
        }

        start_date = response.xpath('//td[contains(text(), "Date :")]/following-sibling::td/text()').get(default="null")
        if start_date != "null":
            dates = re.findall(r"(\d{1,2}) (\w+) (\d{4})", start_date)
            if len(dates) == 2:
                s_day, s_month_en, s_year = dates[0]
                e_day, e_month_en, e_year = dates[1]
                s_month_th = month_map.get(s_month_en, s_month_en)
                e_month_th = month_map.get(e_month_en, e_month_en)
                start_date = f"{s_day} {s_month_th} {s_year}"
                end_date = f"{e_day} {e_month_th} {e_year}"
            elif len(dates) == 1:
                day, month_en, year = dates[0]
                month_th = month_map.get(month_en, month_en)
                start_date = end_date = f"{day} {month_th} {year}"
            else:
                start_date = end_date = "null"
        else:
            start_date = end_date = "null"

        event_slot_time_raw = response.xpath('//td[contains(text(), "Time :")]/following-sibling::td/text()').get(default="null")
        event_slot_time = self.clean_event_time(event_slot_time_raw)
        #event_slot_time = response.xpath('//td[contains(text(), "Time :")]/following-sibling::td/text()').get(default="null")
        location = response.xpath('//td[contains(text(), "Venue :")]/following-sibling::td/text()').get(default="null").strip()

        return start_date, end_date, event_slot_time, location

    def extract_description_and_url(self, response):
        paragraphs = response.css("div.content-detail.event-detail p")
        full_text = " ".join([" ".join(p.css("::text").getall()).strip() for p in paragraphs if p.css("::text").getall()])
        
        # ตัดข้อความหลัง "Contact Event Organizer"
        description = re.split(r"Contact Event Organizer", full_text, 1)[0].strip()

        # เริ่มต้นด้วยค่าว่าง
        event_url = None

        for p in paragraphs:
            if "Contact Event Organizer" in " ".join(p.css("::text").getall()):
                urls = p.css("a::attr(href)").getall()
                for url in urls:
                    if url.startswith("http") and not url.startswith("tel"):
                        event_url = url
                        break
                break

        # ถ้าไม่เจอลิงก์ในเนื้อหา ให้ fallback ไปใช้ URL ของหน้าอีเวนต์นี้
        if not event_url:
            event_url = response.url

        return description if description else "null", event_url

    def extract_time_from_description(self, description):
        time_match = re.search(r"เวลา\s*(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}|\d{1,2}:\d{2})", description)
        return time_match.group(1) if time_match else "null"

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

    def clean_event_time(self, time_str):
        """ แปลงรูปแบบเวลาเช่น '10:30-20:30 hrs.' เป็น '10:30 - 20:30' """
        if not time_str or time_str == "null":
            return "null"

        # ลบคำว่า hrs. หรือ HRS.
        time_str = re.sub(r"\s*hrs\.?", "", time_str, flags=re.IGNORECASE)

        # เพิ่มช่องว่างรอบ - ถ้ายังไม่มี
        time_str = re.sub(r"\s*[-–]\s*", " - ", time_str)

        # ลบช่องว่างเกิน
        time_str = re.sub(r"\s{2,}", " ", time_str).strip()

        return time_str
    
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


