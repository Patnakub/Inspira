import scrapy
import re
import json
import os
import datetime
from scrapy_project.category.predictor import predict_category
import dateparser
import html

class CentralWorldSpider(scrapy.Spider):
    name = "centralworld_spider_upcoming"
    allowed_domains = ["centralworld.co.th"]
    start_urls = [f"https://www.centralworld.co.th/th/events?page={i}" for i in range(1, 11)]  # ดึง 10 หน้า

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.past_event_count = 0  # ✅ ตัวแปรนับจำนวน past event

    def parse(self, response):
        """ ดึงลิงก์อีเวนต์ทั้งหมดจากหน้าหลักของ CentralWorld """
        event_links = response.css("div.card-deck a.card--news::attr(href)").getall()
        full_links = [response.urljoin(link) for link in event_links]

        # วนลูปเข้าไปดึงข้อมูลจากแต่ละลิงก์นิทรรศการ
        for link in full_links:
            yield scrapy.Request(url=link, callback=self.parse_event)

    def parse_event(self, response):
        title = response.css("h1.news-detail__title::text").get(default="null").strip()
        description = self.extract_description(response)

        # ดึงปีจากวันที่โพสต์ ถ้าไม่มีปีในข้อมูลอีเวนต์
        post_date_text = response.css("div.news-detail__date::text").get()
        post_year = re.search(r"(\d{4})", post_date_text) if post_date_text else None
        post_year = post_year.group(1) if post_year else str(datetime.now().year)

        # ดึงข้อมูลวันที่จาก description
        start_date, end_date = self.extract_dates(description, response)

        event_slot_time = "10:00–22:00"

        # กำหนด location
        location = "Central World"

        # URL ของอีเวนต์
        event_urls = "/".join(response.url.split("/")[:6])

        # ดึงข้อมูลบัตรและราคา
        ticket, ticket_price = self.extract_ticket_info(description)

        predicted_categories = predict_category(title, description)

        # ดึง Cover Picture
        cover_picture = response.css("div.col-lg-8.col-xxl-6 figure img::attr(src)").get()

        if not cover_picture:  
            cover_picture = response.css("div.col-lg-8.col-xxl-6 p.text-center img::attr(src)").get()

        cover_picture = f"https://www.centralworld.co.th{cover_picture}" if cover_picture else "null"
        
        reliability_score = 5
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status = determine_status(start_date, end_date)
        if status not in ["upcoming", "ongoing"]:
            self.past_event_count += 1
            if self.past_event_count > 100:
                self.log("🛑 เจอ past event เกิน 30 รายการ — หยุดทำงาน")
                raise scrapy.exceptions.CloseSpider("Too many past events")
            return

        event_data = {
            "title": title if title else "null",
            "description": description if description else "null",
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

        # บันทึกข้อมูลเป็น JSON
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
        """ ดึงรายละเอียดของอีเวนต์แบบไม่มี HTML tag ใด ๆ """
        texts = response.css("div.col-lg-8.col-xxl-6 ::text").getall()
        description = " ".join([t.strip() for t in texts if t.strip()])
        return description if description else "null"


    def extract_dates(self, text, response):
        months = {
            "มกราคม": "มกราคม", "กุมภาพันธ์": "กุมภาพันธ์", "มีนาคม": "มีนาคม", "เมษายน": "เมษายน",
            "พฤษภาคม": "พฤษภาคม", "มิถุนายน": "มิถุนายน", "กรกฎาคม": "กรกฎาคม", "สิงหาคม": "สิงหาคม",
            "กันยายน": "กันยายน", "ตุลาคม": "ตุลาคม", "พฤศจิกายน": "พฤศจิกายน", "ธันวาคม": "ธันวาคม",
            "ม.ค.": "มกราคม", "ก.พ.": "กุมภาพันธ์", "มี.ค.": "มีนาคม", "เม.ย.": "เมษายน",
            "พ.ค.": "พฤษภาคม", "มิ.ย.": "มิถุนายน", "ก.ค.": "กรกฎาคม", "ส.ค.": "สิงหาคม",
            "ก.ย.": "กันยายน", "ต.ค.": "ตุลาคม", "พ.ย.": "พฤศจิกายน", "ธ.ค.": "ธันวาคม",
            "Jan": "มกราคม", "Feb": "กุมภาพันธ์", "Mar": "มีนาคม", "Apr": "เมษายน",
            "May": "พฤษภาคม", "Jun": "มิถุนายน", "Jul": "กรกฎาคม", "Aug": "สิงหาคม",
            "Sep": "กันยายน", "Oct": "ตุลาคม", "Nov": "พฤศจิกายน", "Dec": "ธันวาคม"
        }
        
        post_date_text = response.css("div.news-detail__date::text").get()
        post_year_match = re.search(r"(\d{4})", post_date_text) if post_date_text else None
        post_year = int(post_year_match.group(1)) if post_year_match else datetime.now().year

        # แปลง พ.ศ. เป็น ค.ศ. ถ้าจำเป็น
        if post_year > 2500:
            post_year -= 543

        # **ลำดับความสำคัญ: mixed_pattern มาก่อน!**
        mixed_pattern = r"(\d{1,2})\s*(พฤศจิกายน|ธันวาคม|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|ม.ค.|ก.พ.|มี.ค.|เม.ย.|พ.ค.|มิ.ย.|ก.ค.|ส.ค.|ก.ย.|ต.ค.|พ.ย.|ธ.ค.)\s*-\s*(\d{1,2})\s*(พฤศจิกายน|ธันวาคม|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|ม.ค.|ก.พ.|มี.ค.|เม.ย.|พ.ค.|มิ.ย.|ก.ค.|ส.ค.|ก.ย.|ต.ค.|พ.ย.|ธ.ค.)\s*(\d{4})"
        full_pattern = r"(\d{1,2})\s*(พฤศจิกายน|ธันวาคม|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม)\s*(\d{4})?\s*-\s*(\d{1,2})\s*(พฤศจิกายน|ธันวาคม|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม)\s*(\d{4})?"
        short_pattern = r"(\d{1,2})-(\d{1,2})\s*(พฤศจิกายน|ธันวาคม|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|ม.ค.|ก.พ.|มี.ค.|เม.ย.|พ.ค.|มิ.ย.|ก.ค.|ส.ค.|ก.ย.|ต.ค.|พ.ย.|ธ.ค.)"
        single_with_year_pattern = r"(\d{1,2})\s*(พฤศจิกายน|ธันวาคม|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|ม.ค.|ก.พ.|มี.ค.|เม.ย.|พ.ค.|มิ.ย.|ก.ค.|ส.ค.|ก.ย.|ต.ค.|พ.ย.|ธ.ค.)\s*(\d{2,4})"
        single_pattern = r"^(\d{1,2})\s*(พฤศจิกายน|ธันวาคม|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|ม.ค.|ก.พ.|มี.ค.|เม.ย.|พ.ค.|มิ.ย.|ก.ค.|ส.ค.|ก.ย.|ต.ค.|พ.ย.|ธ.ค.)$"
        this_year_pattern = r"(\d{1,2})\s*-\s*(\d{1,2})\s*(พฤศจิกายน|ธันวาคม|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม)นี้"
        new_this_year_pattern = r"(\d{1,2})\s*(ม.ค.|ก.พ.|มี.ค.|เม.ย.|พ.ค.|มิ.ย.|ก.ค.|ส.ค.|ก.ย.|ต.ค.|พ.ย.|ธ.ค.)\s*นี้"
        range_this_year_pattern = r"(\d{1,2})\s*-\s*(\d{1,2})\s*(ม.ค.|ก.พ.|มี.ค.|เม.ย.|พ.ค.|มิ.ย.|ก.ค.|ส.ค.|ก.ย.|ต.ค.|พ.ย.|ธ.ค.)\s*นี้"
        single_this_year_pattern = r"(\d{1,2})\s*(พฤศจิกายน|ธันวาคม|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม)นี้"
        eng_date_pattern = r"(\d{1,2})\s*([A-Za-z]{3})\s*(\d{4})"
        eng_range_pattern = r"(\d{1,2})\s*-\s*(\d{1,2})\s*([A-Za-z]{3})\s*(\d{4})"
        
        match_mixed = re.search(mixed_pattern, text)
        match_full = re.search(full_pattern, text)
        match_short = re.search(short_pattern, text)
        match_single_with_year = re.search(single_with_year_pattern, text)
        match_single = re.search(single_pattern, text)
        match_this_year = re.search(this_year_pattern, text)
        match_new_this_year = re.search(new_this_year_pattern, text)
        match_range_this_year = re.search(range_this_year_pattern, text)
        match_single_this_year = re.search(single_this_year_pattern, text)
        match_eng_range = re.search(eng_range_pattern, text)
        match_eng_date = re.search(eng_date_pattern, text)
        
        if match_mixed:
            start_day, start_month, end_day, end_month, end_year = match_mixed.groups()
            end_year = int(end_year) - 543  
            start_year = end_year  
            return f"{int(start_day)} {months[start_month]} {start_year}", f"{int(end_day)} {months[end_month]} {end_year}"
        elif match_full:
            start_day, start_month, start_year, end_day, end_month, end_year = match_full.groups()
            start_year = int(start_year) - 543 if start_year else post_year
            end_year = int(end_year) - 543 if end_year else start_year
            return f"{int(start_day)} {months[start_month]} {start_year}", f"{int(end_day)} {months[end_month]} {end_year}"
        elif match_short:
            start_day, end_day, month = match_short.groups()
            return f"{int(start_day)} {months[month]} {post_year}", f"{int(end_day)} {months[month]} {post_year}"
        elif match_single_with_year:
            day, month, year = match_single_with_year.groups()
            year = int(year)
            if year < 100:
                year = (year + 2500) - 543  
            elif year > 2500:
                year = year - 543
            return f"{int(day)} {months[month]} {year}", f"{int(day)} {months[month]} {year}"
        elif match_single:
            day, month = match_single.groups()
            return f"{int(day)} {months[month]} {post_year}", f"{int(day)} {months[month]} {post_year}"
        elif match_this_year:
            start_day, end_day, month = match_this_year.groups()
            return f"{int(start_day)} {months[month]} {post_year}", f"{int(end_day)} {months[month]} {post_year}" 
        elif match_new_this_year:
            day, month = match_new_this_year.groups()
            return f"{int(day)} {months[month]} {post_year}", f"{int(day)} {months[month]} {post_year}"
        elif match_range_this_year:
            start_day, end_day, month = match_range_this_year.groups()
            return f"{int(start_day)} {months[month]} {post_year}", f"{int(end_day)} {months[month]} {post_year}"
        elif match_single_this_year:
            day, month = match_single_this_year.groups()
            return f"{int(day)} {months[month]} {post_year}", f"{int(day)} {months[month]} {post_year}"
        elif match_eng_range:
            start_day, end_day, month, year = match_eng_range.groups()
            month = month.capitalize()  # Normalize ให้เป็น Apr, May, Jun
            year = int(year)
            return f"{int(start_day)} {months[month]} {year}", f"{int(end_day)} {months[month]} {year}"
        elif match_eng_date:
            day, month, year = match_eng_date.groups()
            month = month.capitalize()
            year = int(year)
            return f"{int(day)} {months[month]} {year}", f"{int(day)} {months[month]} {year}"


        return "null", "null"

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

