import scrapy
import re
import json
import os
import datetime
from scrapy_project.category.predictor import predict_category
import dateparser
import html

class ParagonHallSpider(scrapy.Spider):
    name = "paragonhall_spider_full"
    allowed_domains = ["paragonhall.com"]

    def start_requests(self):
        base_url = "https://www.paragonhall.com/th/events/"
        for i in range(1, 61):  # ดึงข้อมูลตั้งแต่ 1 ถึง 60
            yield scrapy.Request(url=f"{base_url}{i}", callback=self.parse_event, errback=self.handle_error)

    def handle_error(self, failure):
        """ ข้าม URL ที่ไม่พบหรือเกิดข้อผิดพลาด """
        self.logger.warning(f"Skipping URL due to error: {failure.request.url}")

    def parse_event(self, response):
        if response.status == 404:  # ถ้าเจอหน้า 404 ข้ามไปลิงก์ถัดไป
            self.logger.info(f"Skipping {response.url} (404 Not Found)")
            return

        title = response.css("div.gold.text-xl.md\:text-3xl.uppercase.mb-5.md\:mb-8.md\:ms-9::text").get(default="null").strip()
        description = self.extract_description(response)
        start_date, end_date = self.extract_dates(response, description)
        event_slot_time = self.extract_event_time(response, description)
        location = self.extract_location(response)
        url = response.css("div.font-medium.pt-1 a.purple::attr(href)").get(default=response.url)
        ticket, ticket_price = self.extract_ticket_info(description)
        cover_picture = response.css("div.pic.mb-10 img.block::attr(src)").get(default="null")
        reliability_score = 5
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        predicted_categories = predict_category(title, description)

        event_data = {
            "title": title,
            "description": description,
            "categories": predicted_categories,
            "start_date": start_date,
            "end_date": end_date,
            "event_slot_time": event_slot_time,
            "location": location,
            "url": url,
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
        raw_data_dir = os.path.join(base_dir, "raw_data", "full")
        os.makedirs(raw_data_dir, exist_ok=True)  # สร้างโฟลเดอร์ถ้ายังไม่มี

        filepath = os.path.join(raw_data_dir, filename)

        # เขียนไฟล์ JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(event_data, f, ensure_ascii=False, indent=4)

        yield event_data

    def extract_event_time(self, response, description):
        times = response.css("div.font-medium span.text-base.md\\:text-xl::text").getall()
        combined_text = " ".join(times).strip()

        # ❶ ตรวจหาแบบ AM/PM ก่อน
        time_matches = re.findall(r"(\d{1,2}:\d{2} (?:AM|PM))", combined_text, re.IGNORECASE)

        if len(time_matches) == 2:
            start_time = self.convert_time_format(time_matches[0])
            end_time = self.convert_time_format(time_matches[1])
            return f"{start_time} - {end_time}"

        elif len(time_matches) == 1:
            start_time = self.convert_time_format(time_matches[0])
            return f"{start_time} - null"

        # ❷ ถ้าไม่พบ AM/PM → ตรวจจาก description แทน
        lower_desc = description.lower()

        # หาแบบ: เวลา 10.00 - 20.00
        match_range = re.search(r"เวลา\s*(\d{1,2})[.:](\d{2})\s*-\s*(\d{1,2})[.:](\d{2})", lower_desc)
        if match_range:
            h1, m1, h2, m2 = match_range.groups()
            start = f"{int(h1):02}:{int(m1):02}"
            end = f"{int(h2):02}:{int(m2):02}"
            return f"{start} - {end}"

        # หาแบบ: เวลา 13.00 หรือ เวลา 9.30
        match_single = re.search(r"เวลา\s*(\d{1,2})[.:](\d{2})", lower_desc)
        if match_single:
            h, m = match_single.groups()
            start = f"{int(h):02}:{int(m):02}"
            return f"{start} - null"

        return "null"


    def convert_time_format(self, time_str):
        try:
            time_obj = datetime.datetime.strptime(time_str.strip(), "%I:%M %p")
            return time_obj.strftime("%H:%M")
        except ValueError:
            return "null"

    def extract_location(self, response):
        location = response.css("div.font-medium.text-base.md\:text-lg::text").get()
        return f"Paragon Hall, {location.strip()}" if location else "Paragon Hall"

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
    
    def extract_dates(self, response, description):
        months = {
            "Jan": "มกราคม", "Feb": "กุมภาพันธ์", "Mar": "มีนาคม", "Apr": "เมษายน",
            "May": "พฤษภาคม", "Jun": "มิถุนายน", "Jul": "กรกฎาคม", "Aug": "สิงหาคม",
            "Sep": "กันยายน", "Oct": "ตุลาคม", "Nov": "พฤศจิกายน", "Dec": "ธันวาคม"
        }

        def extract_year_from_text(text):
            """ ค้นหาปีจาก title หรือ description """
            year_match = re.search(r"(25\d{2})", text)  # พ.ศ.
            if year_match:
                return int(year_match.group(1)) - 543
            year_match = re.search(r"(20\d{2})", text)  # ค.ศ.
            if year_match:
                return int(year_match.group(1))
            return None

        date_text = response.css("div.font-medium.text-base.md\\:text-xl span::text").getall()
        dates = [d.strip() for d in date_text if d.strip()]
        combined_text = " ".join(dates)

        title = response.css("div.gold.text-xl.md\\:text-3xl.uppercase.mb-5.md\\:mb-8.md\\:ms-9::text").get(default="null").strip()
        fallback_year = extract_year_from_text(title + " " + description)
        if not fallback_year:
            fallback_year = datetime.datetime.now().year

        match = re.search(r"(\d{1,2})\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*-\s*(\d{1,2})\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?", combined_text)
        if match:
            start_day, start_month, end_day, end_month = match.groups()
            if not end_month:
                end_month = start_month
            return (
                f"{int(start_day)} {months.get(start_month, start_month)} {fallback_year}",
                f"{int(end_day)} {months.get(end_month, end_month)} {fallback_year}"
            )

        match_single = re.search(r"(\d{1,2})\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", combined_text)
        if match_single:
            day, month = match_single.groups()
            return (
                f"{int(day)} {months.get(month, month)} {fallback_year}",
                f"{int(day)} {months.get(month, month)} {fallback_year}"
            )

        return "null", "null"


    def extract_description(self, response):
        """ ดึงรายละเอียดของอีเวนต์ """
        description_parts = response.css("div.box__description.md\:ms-9 p::text").getall()
        description = " ".join([part.strip() for part in description_parts if part.strip()])
        return description if description else "null"
    
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



