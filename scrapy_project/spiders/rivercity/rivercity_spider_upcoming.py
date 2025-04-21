import scrapy
import re
import json
import joblib
import sys
import os
import datetime
from scrapy_project.category.predictor import predict_category
import dateparser
import html

class RiverCitySpider(scrapy.Spider):
    name = "rivercity_spider_upcoming"
    allowed_domains = ["rivercitybangkok.com"]
    start_year = 2025
    end_year = 2020
    start_urls = [f"https://rivercitybangkok.com/th/category/exhibitions/?pyear={start_year}&keyword="]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.past_event_count = 0  # ✅ ตัวแปรนับจำนวน past event

    def parse(self, response):
        """ ดึง URL ของอีเวนต์จากหน้ารวม """
        event_links = response.css("a.event-item::attr(href)").getall()
        past_event_links = response.css("a.event-item-sm::attr(href)").getall()
        next_page = response.css("a.next.page-numbers::attr(href)").get()

        all_links = event_links + past_event_links

        for link in all_links:
            yield response.follow(link, callback=self.parse_event)

        if next_page:
            yield response.follow(next_page, callback=self.parse)
        else:
            # ดึงปีปัจจุบันจาก URL แล้วลดลงไปเรื่อยๆ จนถึงปี 2020
            current_year = int(response.url.split("pyear=")[-1].split("&")[0])
            if current_year > self.end_year:
                next_year = current_year - 1
                next_year_url = f"https://rivercitybangkok.com/th/category/exhibitions/?pyear={next_year}&keyword="
                yield response.follow(next_year_url, callback=self.parse)


    def parse_event(self, response):
        """ ดึงข้อมูลจากหน้าอีเวนต์ """
        title = response.css("h1.post-title::text").get(default="null").strip()
        description = self.extract_description(response)
        start_date, end_date = self.extract_dates(response)
        event_slot_time = "10:00–20:00"
        location = "River City Bangkok"
        event_urls = response.url
        ticket, ticket_price = self.extract_ticket_info(description)
        cover_picture = self.extract_cover_picture(response)
        predicted_categories = predict_category(title, description)
        reliability_score = 5
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = determine_status(start_date, end_date)
        if status not in ["upcoming", "ongoing"]:
            self.past_event_count += 1
            if self.past_event_count > 30:
                self.log("🛑 เจอ past event เกิน 30 รายการ — หยุดทำงาน")
                raise scrapy.exceptions.CloseSpider("Too many past events")
            return


        event_data = {
            "title": title,
            "description": description,
            "categories": predicted_categories,
            "start_date": start_date,
            "end_date": end_date,
            "event_slot_time": event_slot_time,
            "location": location,
            "url": event_urls,
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

    def extract_description(self, response):
        """ ดึงรายละเอียดของอีเวนต์ """
        description = response.css("div.c-sm p::text").getall()
        description = " ".join(description).strip() if description else "null"
        return description

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

    def extract_dates(self, response):
        """ ดึงข้อมูลวันที่และแปลงตัวย่อเดือนเป็นชื่อเต็ม """
        month_mapping = {
            "ม.ค.": "มกราคม", "ก.พ.": "กุมภาพันธ์", "มี.ค.": "มีนาคม", "เม.ย.": "เมษายน",
            "พ.ค.": "พฤษภาคม", "มิ.ย.": "มิถุนายน", "ก.ค.": "กรกฎาคม", "ส.ค.": "สิงหาคม",
            "ก.ย.": "กันยายน", "ต.ค.": "ตุลาคม", "พ.ย.": "พฤศจิกายน", "ธ.ค.": "ธันวาคม"
        }

        date_text = response.css("time.duration::text, span.duration::text").get(default="null").strip()

        # รูปแบบ 1: "4 ธ.ค. 2024 — 12 ม.ค. 2025"
        match1 = re.search(r"(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*(\d{4})\s*[—-]\s*(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*(\d{4})", date_text)

        # รูปแบบ 2: "7 — 30 มี.ค. 2025"
        match2 = re.search(r"(\d{1,2})\s*[—-]\s*(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*(\d{4})", date_text)

        # รูปแบบ 3: "27 มี.ค.—27 เม.ย. 2025"
        match3 = re.search(r"(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*[—-]\s*(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*(\d{4})", date_text)

        if match1:
            start_day, start_month, start_year, end_day, end_month, end_year = match1.groups()
            start_month_full = month_mapping[start_month]
            end_month_full = month_mapping[end_month]
            return f"{start_day} {start_month_full} {start_year}", f"{end_day} {end_month_full} {end_year}"

        elif match2:
            start_day, end_day, month, year = match2.groups()
            month_full = month_mapping[month]
            return f"{start_day} {month_full} {year}", f"{end_day} {month_full} {year}"

        elif match3:
            start_day, start_month, end_day, end_month, year = match3.groups()
            start_month_full = month_mapping[start_month]
            end_month_full = month_mapping[end_month]
            return f"{start_day} {start_month_full} {year}", f"{end_day} {end_month_full} {year}"

        return "null", "null"

    def extract_cover_picture(self, response):
        """ ดึงรูปภาพจาก <figure class='hero-c'> ผ่าน src """
        cover_picture = response.css("figure.hero-c img.hero-img.skip-lazy::attr(src)").get()
        
        if cover_picture and not cover_picture.startswith("data:image"):
            return cover_picture
        
        return "null"
    
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



