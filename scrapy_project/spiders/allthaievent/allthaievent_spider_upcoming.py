import scrapy
import re
import json
import datetime
import os
from scrapy_project.category.predictor import predict_category
import dateparser
import html

class AllThaiEventSpider(scrapy.Spider):
    name = "allthaievent_spider_upcoming"
    allowed_domains = ["allthaievent.com"]
    start_urls = ["https://www.allthaievent.com/monthlyevents/2025-03-01/"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.past_event_count = 0  # ✅ ตัวแปรนับจำนวน past event

    def parse(self, response):
        """ ดึงลิงก์อีเว้นท์จากหน้ารวม แล้วไปเก็บข้อมูลแต่ละอีเว้นท์ """
        event_count = 0
        for event in response.css("div.thumbnail-xs"):
            relative_link = event.css("a::attr(href)").get()
            full_link = response.urljoin(relative_link)
            title = event.css("strong::text").get()

            if full_link and title:
                event_count += 1
                self.log(f"🔄 กำลังดึงข้อมูลจาก: {title}")
                yield response.follow(full_link, self.parse_event, meta={"title": title.strip()})

        if event_count == 0:
            self.log(f"🛑 ไม่พบอีเว้นท์ในลิงก์: {response.url} — หยุดทำงาน")
            return

        # ✅ แยกปีและเดือนจาก URL เช่น: 2025-03-01
        current_date_str = response.url.rstrip("/").split("/")[-1]  # 2025-03-01
        year, month, day = current_date_str.split("-")
        year = int(year)
        month = int(month)

        # ✅ เพิ่มเดือน
        month += 1
        if month > 12:
            month = 1
            year += 1

        # ✅ สร้าง URL ใหม่โดยเปลี่ยนเฉพาะเลขเดือน
        next_month_str = f"{year}-{month:02d}-01"
        next_url = f"https://www.allthaievent.com/monthlyevents/{next_month_str}/"

        self.log(f"➡️ ไปยังเดือนถัดไป: {next_url}")
        yield scrapy.Request(next_url, callback=self.parse)

    def parse_event(self, response):
        """ ดึงข้อมูลของอีเว้นท์แต่ละอัน แล้วเซฟเป็นไฟล์ JSON ชื่อตาม `title` """
        title = response.meta.get("title", "No title")

        # ✅ ดึงคำอธิบาย (Description)
        description = self.extract_description(response)

        # ✅ ดึงข้อมูลวันที่, เวลา, และสถานที่ (จากข้อความสีส้ม)
        date_info = response.css("span[style*='#ff6600']::text").getall()
        start_date, end_date, event_slot_time, location = self.extract_event_details(date_info)

        # ✅ ลิสต์ชื่อจังหวัด (ยกเว้นกรุงเทพฯ)
        provinces = [
            "กระบี่", "กาญจนบุรี", "กาฬสินธุ์", "กำแพงเพชร", "ขอนแก่น", "จันทบุรี", "ฉะเชิงเทรา", "ชลบุรี",
            "ชัยนาท", "ชัยภูมิ", "ชุมพร", "เชียงราย", "เชียงใหม่", "ตรัง", "ตราด", "ตาก", "นครนายก",
            "นครปฐม", "นครพนม", "นครราชสีมา", "นครศรีธรรมราช", "นครสวรรค์", "นนทบุรี", "นราธิวาส",
            "น่าน", "บึงกาฬ", "บุรีรัมย์", "ปทุมธานี", "ประจวบคีรีขันธ์", "ปราจีนบุรี", "ปัตตานี", "พระนครศรีอยุธยา",
            "พังงา", "พัทลุง", "พิจิตร", "พิษณุโลก", "เพชรบุรี", "เพชรบูรณ์", "แพร่", "พะเยา", "ภูเก็ต",
            "มหาสารคาม", "มุกดาหาร", "แม่ฮ่องสอน", "ยโสธร", "ยะลา", "ร้อยเอ็ด", "ระนอง", "ระยอง", "ราชบุรี",
            "ลพบุรี", "ลำปาง", "ลำพูน", "เลย", "ศรีสะเกษ", "สกลนคร", "สงขลา", "สตูล", "สมุทรปราการ",
            "สมุทรสงคราม", "สมุทรสาคร", "สระแก้ว", "สระบุรี", "สิงห์บุรี", "สุโขทัย", "สุพรรณบุรี", "สุราษฎร์ธานี",
            "สุรินทร์", "หนองคาย", "หนองบัวลำภู", "อ่างทอง", "อำนาจเจริญ", "อุดรธานี","อุดร", "อุตรดิตถ์",
            "อุทัยธานี", "อุบลราชธานี"
        ]

        # ✅ ตรวจสอบชื่อจังหวัดใน location (ยกเว้นกรุงเทพฯ)
        if location:
            for province in provinces:
                if province in location:
                    self.log(f"⏭️ ข้ามอีเว้นท์ '{title}' เพราะอยู่ในจังหวัด: {province}")
                    return  # ข้ามอีเว้นท์นี้
                
        status = determine_status(start_date, end_date)
        if status not in ["upcoming", "ongoing"]:
            self.past_event_count += 1
            if self.past_event_count > 30:
                self.log("🛑 เจอ past event เกิน 30 รายการ — หยุดทำงาน")
                raise scrapy.exceptions.CloseSpider("Too many past events")
            return

        # ✅ ดึง URL (Facebook ก่อน, ถ้าไม่มีให้ใช้ Website)
        facebook_url = response.xpath("//span[@style='color: #339966;']//a[contains(@href, 'facebook.com')]/@href").get()
        if not facebook_url:
            facebook_url = response.xpath("//a[contains(@href, 'facebook.com')][not(contains(@href, 'allthaievent'))]/@href").get()
            
        website_url = response.xpath("//span[@style='color: #339966;']//a[contains(@href, 'http')][not(contains(@href, 'facebook.com'))]/@href").get()
        event_url = facebook_url if facebook_url else website_url if website_url else "N/A"

        # ✅ ดึง Cover Picture
        cover_picture = response.css("a#evimg::attr(href)").get()

        # ✅ ดึงข้อมูลบัตรและราคา
        ticket, ticket_price = self.extract_ticket_info(description)

        # ✅ ทำนายหมวดหมู่
        predicted_categories = predict_category(title, description)

        reliability_score = 2
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        event_data = {
            "title": title,
            "description": description if description else "No description",
            "categories": predicted_categories,
            "start_date": start_date,
            "end_date": end_date,
            "event_slot_time": event_slot_time,
            "location": location,
            "url": event_url,
            "cover_picture": cover_picture,
            "ticket": ticket,
            "ticket_price": ticket_price,
            "reliability_score": reliability_score,
            "timestamp": timestamp,
            "status": determine_status(start_date, end_date)
        }

        # ✅ สร้างชื่อไฟล์ JSON
        filename = re.sub(r"[\\/:*?\"<>|]", "_", title) + ".json"

        # ✅ กำหนดโฟลเดอร์สำหรับเซฟไฟล์
        base_dir = os.path.dirname(os.path.abspath(__file__))
        raw_data_dir = os.path.join(base_dir, "raw_data", "upcoming")
        os.makedirs(raw_data_dir, exist_ok=True)

        filepath = os.path.join(raw_data_dir, filename)

        # ✅ เขียนไฟล์ JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(event_data, f, ensure_ascii=False, indent=4)

        yield event_data


    def extract_description(self, response):
        """ ดึง #text ทั้งหมดจาก <div class="separated-border"> ก่อนถึงข้อความสีส้ม """
        description_text = []
        elements = response.css("div.separated-border *::text").getall()

        for text in elements:
            text = text.strip()
            if not text:
                continue

            # หยุดดึงเมื่อถึงข้อความสีส้ม (วันที่, เวลา, สถานที่)
            if "วันที่ :" in text or "เวลา :" in text or "สถานที่ :" in text:
                break

            description_text.append(text)

        return " ".join(description_text).strip()

    def extract_event_details(self, date_info):
        start_date, end_date = None, None
        event_slot_time, location = None, None


        if date_info:
            details_text = " ".join(date_info)

            # ✅ ดึงข้อมูลวันที่
            extracted_start, extracted_end = self.extract_dates(details_text)
            if extracted_start != "ไม่ระบุ":
                start_date, end_date = extracted_start, extracted_end

            # ✅ ดึงข้อมูลเวลา: ให้หาเฉพาะจาก "เวลา : ..." เท่านั้น
            for line in date_info:
                if "เวลา" in line:
                    time_match = re.search(r"เวลา\s*:\s*(.+)", line)
                    if time_match:
                        event_slot_time = time_match.group(1).strip()
                        event_slot_time = re.sub(r"\s*-\s*", "-", event_slot_time)  # ลบช่องว่างรอบ "-"
                        event_slot_time = re.sub(r"\s*น\.*", "", event_slot_time)  # ลบ "น." หรือ "น"
                        break

            # ✅ ดึงข้อมูลสถานที่
            for line in date_info:
                if "สถานที่" in line:
                    location_match = re.search(r"สถานที่\s*:\s*(.+)", line)
                    if location_match:
                        location = location_match.group(1).strip()
                        break

        return start_date, end_date, event_slot_time, location

    def extract_dates(self, text):
        """ ดึงวันที่จากข้อความ และแปลงปี พ.ศ. เป็น ค.ศ. """
        months = {
            "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
            "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12
        }

        today = datetime.datetime.today()
        thai_today_date = f"{today.day} {list(months.keys())[today.month - 1]} {today.year}"

        patterns = [
            (r"(\d{1,2})\s*-\s*(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})", 2),
            (r"(?:ตั้งแต่(?:วันที่)?\s*)?(\d{1,2}|วันนี้)\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)?(?:\s*(\d{4}))?\s*(?:จนถึง|ถึง|-)\s*(?:วันที่\s*)?(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)(?:\s*(\d{4}))?", 1),
            (r"วันที่\s*(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})", 3)
        ]

        for pattern, group_count in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()

                if group_count == 2:
                    start_day, end_day, month, year = groups
                    year = int(year) - 543
                    return f"{int(start_day)} {month} {year}", f"{int(end_day)} {month} {year}"

                elif group_count == 1:
                    start_day, start_month, start_year, end_day, end_month, end_year = groups

                    if start_day == "วันนี้":
                        start_date_text = thai_today_date
                    else:
                        start_year = int(start_year) - 543 if start_year else None
                        end_year = int(end_year) - 543 if end_year else start_year

                        if start_day and start_month and start_year:
                            start_date_text = f"{int(start_day)} {start_month} {start_year}"
                        else:
                            start_date_text = None

                    if end_day and end_month and end_year:
                        end_date_text = f"{int(end_day)} {end_month} {end_year}"
                    else:
                        end_date_text = None

                    return start_date_text, end_date_text

                elif group_count == 3:
                    day, month, year = groups
                    year = int(year) - 543
                    return f"{int(day)} {month} {year}", None

        return None, None


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

