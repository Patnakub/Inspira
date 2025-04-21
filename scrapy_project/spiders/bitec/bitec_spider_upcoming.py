import scrapy
import re
import json
import os
import datetime
from scrapy_project.category.predictor import predict_category
import dateparser
import html

class BitecSpider(scrapy.Spider):
    name = "bitec_spider_upcoming"
    allowed_domains = ["bitec.co.th"]
    handle_httpstatus_list = [500] 


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ตัวแปรเดิม
        self.current_year = 2025
        self.current_month = 3
        self.current_page = 1
        self.empty_month_count = 0  # นับจำนวนเดือนที่ไม่มีข้อมูลติดกัน
        self.past_event_count = 0  # นับจำนวน past event

    def start_requests(self):
        url = self.build_url(self.current_year, self.current_month, self.current_page)
        yield scrapy.Request(url=url, callback=self.parse)

    def build_url(self, year, month, page):
        return f"https://www.bitec.co.th/wp-json/bitec/v1/events?page={page}&year={year}&month={month:02d}"

    def parse(self, response):
        # ตรวจสอบถ้าเซิร์ฟเวอร์ส่งสถานะ 500 (Internal Server Error)
        if response.status == 500:
            self.logger.warning(f"API error 500 at {response.url}, skipping to next month.")
            self.empty_month_count += 1
            yield from self.advance_to_next_month()
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.warning(f"Invalid JSON response at {response.url}, skipping.")
            self.empty_month_count += 1
            yield from self.advance_to_next_month()
            return

        if data:
            self.empty_month_count = 0  # รีเซ็ตตัวนับเดือนว่าง
            for event in data:
                link = event.get("link")
                if link:
                    # เพิ่ม /th/ หลัง domain
                    modified_link = link.replace("https://www.bitec.co.th/", "https://www.bitec.co.th/th/")
                    yield scrapy.Request(url=modified_link, callback=self.parse_event)

            # ไปหน้า page ถัดไปของเดือนปัจจุบัน
            self.current_page += 1
            next_url = self.build_url(self.current_year, self.current_month, self.current_page)
            yield scrapy.Request(url=next_url, callback=self.parse)
        else:
            # ถ้า page นี้ไม่มีข้อมูล → ข้ามไปเดือนถัดไป
            self.logger.info(f"No data at {response.url}, moving to next month.")
            self.empty_month_count += 1
            yield from self.advance_to_next_month()

    def advance_to_next_month(self):
        self.current_page = 1
        self.current_month += 1

        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1

        if self.empty_month_count >= 10:
            self.logger.info("No data or server errors for 3 consecutive months. Stopping spider.")
            return  # ไม่ yield ต่อ = หยุด spider

        next_url = self.build_url(self.current_year, self.current_month, self.current_page)
        yield scrapy.Request(url=next_url, callback=self.parse)


    def parse_event(self, response):
        # >>> โค้ดเก็บข้อมูลจากหน้า event <<< 
        self.logger.info(f"Processing event page: {response.url}")
        title = response.css("h2.entry-title a::text").get(default="null").strip()

        # ดึงข้อมูลวันที่จาก <header class="entry-header">
        date_text = response.css("header.entry-header p.date::text").get(default="null").strip()
        start_date, end_date = self.extract_dates_from_header(date_text)

        # ดึงข้อมูลสถานที่จาก <header class="entry-header">
        location_text = response.css("header.entry-header p.venue::text").get(default="null").strip()
        location = self.clean_location(location_text)

        # ดึงข้อมูลรายละเอียดอีเวนต์
        description = self.extract_description(response)

        # ดึงข้อมูลเวลา
        time_text = self.extract_text_by_keyword(response, ['เวลา', 'Time'])
        event_slot_time = self.extract_time(time_text)

        # หาก event_slot_time เป็น "null" หรือ " - " ให้ลองหาใน description แทน
        if event_slot_time == "null" or event_slot_time == " - ":
            event_slot_time = self.extract_time(description)

        # URL ของอีเวนต์
        event_urls = self.extract_event_url(response)

        status = determine_status(start_date, end_date)
        if status not in ["upcoming", "ongoing"]:
            self.past_event_count += 1
            if self.past_event_count > 30:
                self.log("🛑 เจอ past event เกิน 30 รายการ — หยุดทำงาน")
                raise scrapy.exceptions.CloseSpider("Too many past events")
            return

        # บัตรและราคา
        ticket, ticket_price = self.extract_ticket_info(description)

        # ดึง Cover Picture
        cover_picture = response.css("div.pic a img::attr(src)").get(default="null")

        reliability_score = 5
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        predicted_categories = predict_category(title, description)

        event_data = {
            "title": title if title else "null",
            "description": description,
            "categories": predicted_categories,
            "start_date": start_date,
            "end_date": end_date,
            "event_slot_time": event_slot_time if event_slot_time != "null" else " - ",
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
        """ ดึงรายละเอียดของอีเวนต์ แล้วทำความสะอาดข้อความโดยลบ \n, \t, ฯลฯ """
        description_parts = []

        for p in response.css("div.entry-content p"):
            text = p.xpath("string(.)").get().strip()

            # หยุดเมื่อเจอคำว่า "สอบถาม" หรือ "more information"
            if any(keyword in text.lower() for keyword in ["สอบถาม", "more information"]):
                break

            # ข้ามข้อความที่เป็นหัวข้อ
            if not any(keyword in text.lower() for keyword in ["วันที่", "เวลา", "สถานที่", "date", "time", "venue"]):
                description_parts.append(text)

        if not description_parts:
            return "null"

        # รวมข้อความทั้งหมด
        combined_text = " ".join(description_parts)

        # ลบ \n, \t, \r และเว้นวรรคซ้ำ ๆ
        cleaned_text = re.sub(r"[\n\r\t]+", " ", combined_text)
        cleaned_text = re.sub(r"\s{2,}", " ", cleaned_text).strip()

        return cleaned_text

    def extract_text_by_keyword(self, response, keywords):
        for p in response.css("div.entry-content p"):
            text = p.xpath("string(.)").get().strip()

            # ตรวจสอบว่าในข้อความมี keyword ที่ต้องการ
            if any(keyword in text for keyword in keywords):
                return text  # คืนค่าข้อความแรกที่ตรงกับ keyword

        return "null"


    def extract_dates_from_header(self, text):
        month_map = {
            "January": "มกราคม", "February": "กุมภาพันธ์", "March": "มีนาคม", "April": "เมษายน",
            "May": "พฤษภาคม", "June": "มิถุนายน", "July": "กรกฎาคม", "August": "สิงหาคม",
            "September": "กันยายน", "October": "ตุลาคม", "November": "พฤศจิกายน", "December": "ธันวาคม"
        }

        pattern_range = r"(\d{1,2})\s*-\s*(\d{1,2})\s*(\w+)\s*(\d{4})"
        pattern_single = r"(\d{1,2})\s*(\w+)\s*(\d{4})"

        match_range = re.search(pattern_range, text)
        match_single = re.search(pattern_single, text)

        if match_range:
            start_day = int(match_range.group(1))
            end_day = int(match_range.group(2))
            month = match_range.group(3)
            year = int(match_range.group(4)) + 543  # แปลง ค.ศ. เป็น พ.ศ.

            month_th = month_map.get(month, month)  # แปลงชื่อเดือนเป็นภาษาไทย
            return f"{start_day} {month_th} {year}", f"{end_day} {month_th} {year}"

        elif match_single:
            day = int(match_single.group(1))
            month = match_single.group(2)
            year = int(match_single.group(3)) + 543

            month_th = month_map.get(month, month)
            return f"{day} {month_th} {year}", f"{day} {month_th} {year}"

        return "null", "null"


    def extract_time(self, text):
        # ลบช่องว่างส่วนเกินออกก่อน
        text = re.sub(r'\s+', ' ', text).strip()

        # ฟังก์ชันแปลง AM/PM เป็นรูปแบบ 24 ชั่วโมง
        def convert_to_24h(time_str):
            match = re.match(r"(\d{1,2})([:.]\d{2})?\s*(AM|PM)", time_str, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                minute = match.group(2) if match.group(2) else ":00"
                period = match.group(3).upper()

                if period == "PM" and hour != 12:
                    hour += 12
                if period == "AM" and hour == 12:
                    hour = 0

                return f"{hour:02d}{minute}".replace(".", ":")  # แปลง 10.00 เป็น 10:00
            return time_str  # คืนค่าเดิมหากไม่มีการเปลี่ยนแปลง

        # รองรับช่วงเวลา เช่น "09.00 – 19.00 น.", "7:00 – 17:00", "13.00 -16.00 น."
        pattern = r"(\d{1,2}[:.]\d{2})\s*[–\-]\s*(\d{1,2}[:.]\d{2})\s*(น\.?)?"

        # รองรับ "(เริ่มการแสดง HH.MM - HH.MM น.)"
        show_pattern = r"\(เริ่มการแสดง\s*(\d{1,2}[:.]\d{2})\s*[–\-]\s*(\d{1,2}[:.]\d{2})\s*น?\.\)"

        # รองรับ "รอบ X: HH:MM น."
        round_pattern = r"รอบ\s*\d+[:\s]*(\d{1,2}[:.]\d{2})\s*(น\.?)?"

        # รองรับ "เวลา HH:MM น."
        single_time_pattern = r"เวลา[:\s]*(\d{1,2}[:.]\d{2})\s*(น\.?)?"

        # รองรับ "Time: 10am-6pm"
        am_pm_pattern = r"Time[:\s]*(\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM))\s*[-–]\s*(\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM))"

        # รองรับ "Time 6 pm"
        single_am_pm_pattern = r"Time[:\s]*(\d{1,2}(?:[:.]\d{2})?)\s*(AM|PM)"

        # รองรับ "Time: 10.00 AM. – 09.00 PM."
        detailed_am_pm_pattern = r"Time[:\s]*(\d{1,2}[:.]\d{2})\s*(AM|PM)\s*[–\-]\s*(\d{1,2}[:.]\d{2})\s*(AM|PM)\."

        match = re.search(pattern, text)
        show_match = re.search(show_pattern, text)
        round_match = re.search(round_pattern, text)
        single_time_match = re.search(single_time_pattern, text)
        am_pm_match = re.search(am_pm_pattern, text)
        single_am_pm_match = re.search(single_am_pm_pattern, text)
        detailed_am_pm_match = re.search(detailed_am_pm_pattern, text)

        # ตรวจสอบช่วงเวลาปกติ
        if match:
            start_time = match.group(1).replace(".", ":")
            end_time = match.group(2).replace(".", ":")
            return f"{start_time} - {end_time}"

        # ตรวจสอบ "(เริ่มการแสดง HH.MM - HH.MM น.)"
        if show_match:
            start_time = show_match.group(1).replace(".", ":")
            end_time = show_match.group(2).replace(".", ":")
            return f"{start_time} - {end_time}"

        # ตรวจสอบ "รอบ X: HH:MM น."
        if round_match:
            return round_match.group(1).replace(".", ":")

        # ตรวจสอบ "เวลา HH:MM น."
        if single_time_match:
            return single_time_match.group(1).replace(".", ":")

        # ตรวจสอบ "Time: 10am-6pm"
        if am_pm_match:
            start_time = convert_to_24h(am_pm_match.group(1))
            end_time = convert_to_24h(am_pm_match.group(2))
            return f"{start_time} - {end_time}"

        # ตรวจสอบ "Time 6 pm"
        if single_am_pm_match:
            return convert_to_24h(single_am_pm_match.group(1) + " " + single_am_pm_match.group(2))

        # ตรวจสอบ "Time: 10.00 AM. – 09.00 PM."
        if detailed_am_pm_match:
            start_time = convert_to_24h(detailed_am_pm_match.group(1) + " " + detailed_am_pm_match.group(2))
            end_time = convert_to_24h(detailed_am_pm_match.group(3) + " " + detailed_am_pm_match.group(4))
            return f"{start_time} - {end_time}"

        return "null"


    def clean_location(self, location):
        if location == "null":
            return "null"

        # ลบคำว่า "BITEC" หรือ "ไบเทค" ที่อาจซ้ำซ้อน
        location = re.sub(r"\b(BITEC|ไบเทค)\b", "", location, flags=re.IGNORECASE).strip()

        # เติมคำว่า "Bitec " นำหน้า
        cleaned_location = f"Bitec {location}"

        # ลบ "," ตัวสุดท้ายออกถ้ามี
        cleaned_location = re.sub(r",\s*$", "", cleaned_location)

        return cleaned_location


    def extract_event_url(self, response):
        paragraphs = response.css("div.entry-content p")  # ดึง <p> ทั้งหมด
        found_inquiry = False  # ตัวแปรบอกว่าเจอ "สอบถาม" หรือ "more information" แล้วหรือไม่

        for p in paragraphs:
            text = p.xpath("string(.)").get().strip().lower()

            # ถ้าเจอคำว่า "สอบถาม" หรือ "more information"
            if "สอบถาม" in text or "more information" in text:
                found_inquiry = True  # เริ่มค้นหาลิงก์ใน p ถัดไป
                continue

            # ถ้าเคยเจอ "สอบถาม" หรือ "more information" แล้ว ให้เริ่มมองหาลิงก์
            if found_inquiry:
                links = p.css("a::attr(href)").getall()
                if links:
                    return links[0]  # ดึงลิงก์แรกที่เจอ

        return response.url  # ถ้าไม่เจอลิงก์เลย ให้ใช้ URL ของหน้าเว็บแทน

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
    
def convert_thai_year(text):
    match = re.search(r"(\d{1,2})\s+([^\s]+)\s+(\d{4})", text)
    if match:
        day, month, year = match.groups()
        year = int(year)
        if year > 2500:
            year -= 543
        return f"{day} {month} {year}"
    return text


def determine_status(start_date, end_date):
    today = datetime.date.today()
    start = dateparser.parse(convert_thai_year(start_date), languages=["th", "en"])
    end = dateparser.parse(convert_thai_year(end_date), languages=["th", "en"])

    if not start or not end:
        return "unknown"

    if today < start.date():
        return "upcoming"
    elif start.date() <= today <= end.date():
        return "ongoing"
    else:
        return "past"
