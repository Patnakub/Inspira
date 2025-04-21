import scrapy
import re
import json
import os
from urllib.parse import urljoin
import datetime
from functools import partial
from scrapy_project.category.predictor import predict_category
import dateparser
import html

class BACCSpider(scrapy.Spider):
    name = "bacc_spider_full"
    allowed_domains = ["bacc.or.th"]
    start_urls = ["https://www.bacc.or.th/whats-on/page/1"]

    def parse(self, response):
        """ ดึงลิงก์ของนิทรรศการทั้งหมดจากหน้าหลัก """
        event_links = response.css("div.card.event a.card-link::attr(href)").getall()

        if not event_links:  
            self.logger.info("No more events found. Stopping the crawl.")
            return  

        for link in event_links:
            yield response.follow(link, callback=partial(self.parse_event, from_past=True))

        # ดึงลิงก์ของ pagination ทั้งหมด
        pagination_links = response.css("ul.pagination li.page-item a.page-link::attr(href)").getall()

        # ค้นหาหน้าสูงสุดที่มีในลิงก์ Pagination
        current_page = int(response.url.split("/")[-1])
        next_pages = [int(re.search(r'page/(\d+)', link).group(1)) for link in pagination_links if re.search(r'page/(\d+)', link)]
        
        # หาหน้าถัดไปที่มากกว่าหน้าปัจจุบัน
        next_page = min([p for p in next_pages if p > current_page], default=None)

        if next_page:
            next_page_url = f"https://www.bacc.or.th/whats-on/page/{next_page}"
            self.logger.info(f"Following next page: {next_page_url}")
            yield response.follow(next_page_url, self.parse)
        else:
            # หลังจาก Crawl "What's On" เสร็จแล้ว ไปยังหน้า "Upcoming"
            self.logger.info("Finished crawling What's On, now moving to Upcoming events.")
            yield scrapy.Request(url="https://www.bacc.or.th/whats-on/upcoming", callback=self.parse_upcoming)

    def parse_upcoming(self, response):
        """ ดึงลิงก์ของนิทรรศการจากหน้า Upcoming """
        event_links = response.css("div.card.event a.card-link::attr(href)").getall()
        
        if not event_links:
            self.logger.info("No upcoming events found.")
            return  

        for link in event_links:
            yield response.follow(link, self.parse_event)

        # หลังจากดึง upcoming เสร็จ ไปยังหน้า events
        self.logger.info("Finished crawling Upcoming, now moving to Past events.")
        yield scrapy.Request(url="https://www.bacc.or.th/events/page/1", callback=self.parse_past_events)


    def parse_event(self, response, from_past=False):
        """ เข้าไปดึงข้อมูลรายละเอียดในแต่ละอีเวนต์ """
        title = response.css("h3.mb-3::text").get(default="null").strip()

        # ตรวจสอบว่ามีไฟล์ JSON ของนิทรรศการนี้แล้วหรือไม่
        filename = self.sanitize_filename(title) + ".json"

        base_dir = os.path.dirname(os.path.abspath(__file__))
        raw_data_dir = os.path.join(base_dir, "raw_data")
        os.makedirs(raw_data_dir, exist_ok=True)
        filepath = os.path.join(raw_data_dir, filename)

        if os.path.exists(filepath):
            self.logger.info(f"Skipping already scraped event: {title}")
            return

        # ดึงข้อมูลวันที่
        date_text = response.xpath("string(//div[contains(@class, 'sb-box when')])").get()
        date_text = date_text.strip() if date_text else "null"

        start_date, end_date = self.extract_dates(date_text)

        # ✅ หากเป็นข้อมูลจาก /events และวันที่เริ่ม < 2020-01-01 ให้หยุด
        if from_past and self.is_before_2020(start_date):
            self.logger.info(f"Reached event before 2020: {start_date} — Stopping crawl.")
            raise scrapy.exceptions.CloseSpider("Reached event before 2020.")

        event_slot_time = "10.00-20.00"

        # ดึงข้อมูลสถานที่
        location = self.extract_location(response)

        # ดึงข้อมูลรายละเอียดอีเวนต์
        description = self.extract_description(response)

        # URL ของอีเวนต์
        event_urls = response.url

        # บัตรและราคา
        ticket, ticket_price = self.extract_ticket_info(description)
        # ดึง Cover Picture
        cover_picture = response.css("figure.wp-block-image a::attr(href)").get(default="null")

        reliability_score = 5
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        predicted_categories = predict_category(title, description)

        event_data = {
            "title": title if title else "null",
            "description": description if description else "null",
            "categories": predicted_categories,
            "start_date": start_date,
            "end_date": end_date,
            "event_slot_time": event_slot_time,
            "location": f"BACC {location}" if location != "null" else "null",
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
        raw_data_dir = os.path.join(base_dir, "raw_data", "full")
        os.makedirs(raw_data_dir, exist_ok=True)  # สร้างโฟลเดอร์ถ้ายังไม่มี

        filepath = os.path.join(raw_data_dir, filename)

        # เขียนไฟล์ JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(event_data, f, ensure_ascii=False, indent=4)

        yield event_data

    def extract_location(self, response):
        """ ดึงข้อมูลสถานที่ """
        location = response.xpath("string(//div[contains(@class, 'sb-box location')])").get()
        location = location.strip().replace("\n", " ") if location else "null"
        return location

    def extract_description(self, response):
        """ ดึงรายละเอียดของอีเวนต์ เก็บข้อความจาก <p> ตั้งแต่ตัวที่ 2 เป็นต้นไป รวมถึงลิงก์ใน <a> """
        paragraphs = response.css("div.entry p:nth-of-type(n+2)")
        description = []

        for p in paragraphs:
            text = p.css("::text").getall()
            text = " ".join([t.strip() for t in text if t.strip()])

            # ตรวจหาลิงก์ใน <a>
            link = p.css("a::attr(href)").get()
            if link:
                text += f" ({link})"

            if text:
                description.append(text)

        return " ".join(description) if description else "null"

    def extract_dates(self, text):
        """ ฟังก์ชันดึงวันที่จากข้อความ รองรับช่วงวันที่ วันเดียว และแปลง พ.ศ. → ค.ศ. """

        def to_ad_year(year):
            year = int(year)
            return year - 543 if year > 2500 else year  # ถ้าเป็น พ.ศ. ให้ลบ 543

        # กรณี 1: ช่วงวันที่ต่างปี เช่น "03 กรกฎาคม 2567 - 31 ธันวาคม 2568"
        full_range_pattern = r"(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})\s*-\s*(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})"
        match = re.search(full_range_pattern, text)

        if match:
            start_day, start_month, start_year, end_day, end_month, end_year = match.groups()
            return (
                f"{int(start_day)} {start_month} {to_ad_year(start_year)}",
                f"{int(end_day)} {end_month} {to_ad_year(end_year)}"
            )

        # กรณี 2: ช่วงวันที่ปีเดียวกัน เช่น "5 มีนาคม - 30 มีนาคม 2568"
        range_pattern = r"(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*-\s*(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})"
        match = re.search(range_pattern, text)

        if match:
            start_day, start_month, end_day, end_month, year = match.groups()
            year = to_ad_year(year)
            return (
                f"{int(start_day)} {start_month} {year}",
                f"{int(end_day)} {end_month} {year}"
            )

        # กรณี 3: วันเดียว เช่น "02 กุมภาพันธ์ 2563"
        single_pattern = r"(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})"
        match = re.search(single_pattern, text)

        if match:
            day, month, year = match.groups()
            year = to_ad_year(year)
            return f"{int(day)} {month} {year}", f"{int(day)} {month} {year}"

        return "null", "null"


    def sanitize_filename(self, title):
        """ ฟังก์ชันล้างชื่อไฟล์ให้ถูกต้อง """
        invalid_chars = r'[\\/:*?"<>|]'
        return re.sub(invalid_chars, "_", title).strip()
    
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

    
    def parse_past_events(self, response):
        """ ดึงนิทรรศการจากหน้ารวมอีเวนต์ที่ผ่านมา """
        event_links = response.css("div.card.event a.card-link::attr(href)").getall()

        if not event_links:
            self.logger.info("No past events found.")
            return

        for link in event_links:
            yield response.follow(link, callback=lambda r, **kwargs: self.parse_event(r, from_past=True))

        # Pagination
        pagination_links = response.css("ul.pagination li.page-item a.page-link::attr(href)").getall()
        current_page = int(response.url.split("/")[-1])
        next_pages = [int(re.search(r'page/(\d+)', link).group(1)) for link in pagination_links if re.search(r'page/(\d+)', link)]
        next_page = min([p for p in next_pages if p > current_page], default=None)

        if next_page:
            next_page_url = f"https://www.bacc.or.th/events/page/{next_page}"
            self.logger.info(f"Following next past event page: {next_page_url}")
            yield response.follow(next_page_url, self.parse_past_events)

    def is_before_2020(self, start_date_str):
        """ ตรวจสอบว่า start_date < 1 มกราคม 2020 """
        try:
            months = {
                "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
                "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
                "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12
            }

            parts = start_date_str.split()
            if len(parts) != 3:
                return False

            day = int(parts[0])
            month = months.get(parts[1], 1)
            year = int(parts[2])
            date = datetime.date(year, month, day)

            return date < datetime.date(2020, 1, 1)

        except Exception as e:
            self.logger.warning(f"Failed to parse start_date '{start_date_str}': {e}")
            return False
        
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



