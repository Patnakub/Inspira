import scrapy
import json
import os
import re
from w3lib.html import remove_tags
import datetime
from scrapy_project.category.predictor import predict_category
import dateparser
import html


class EventSpider(scrapy.Spider):
    name = 'thailandexhibition_spider_full'
    base_url = "https://api.thailandexhibition.com/api/trade-shows"
    last_event_time = None  # ใช้เก็บค่าของ event ล่าสุด

    def start_requests(self):
        url = self.get_next_url()
        headers = self.get_headers()
        yield scrapy.Request(url, headers=headers, callback=self.parse)

    def get_next_url(self):
        """สร้าง URL สำหรับโหลดข้อมูลเพิ่ม"""
        if self.last_event_time:
            return f"{self.base_url}?locale=th&filters[menu_of_event][$contains]=thai_events&filters[isPublish][$eq]=true&filters[event_time_sort][$gt]={self.last_event_time}&sort[0]=event_time_sort&sort[1]=view:desc"
        else:
            return f"{self.base_url}?locale=th&filters[menu_of_event][$contains]=thai_events&filters[isPublish][$eq]=true&sort[0]=event_time_sort&sort[1]=view:desc"

    def get_headers(self):
        """ตั้งค่า Headers"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.thailandexhibition.com/thai-event-lists',
            'Origin': 'https://www.thailandexhibition.com'
        }

    def parse(self, response):
        try:
            data = json.loads(response.text)

            if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                for event in data['data']:
                    attributes = event.get('attributes', {})
                    country = attributes.get('country', '').strip()
                    place = attributes.get('place', '').strip()

                    # ขอบเขตการดึงข้อมูล
                    if not (
                        country == "กรุงเทพมหานคร" or
                        (country == "นนทบุรี" and place == "อิมแพ็ค อารีน่า - IMPACT Arena")
                    ):
                        continue  # ข้าม event ที่ไม่เข้าเงื่อนไข

                    event_id = event.get('id')
                    details_url = f"{self.base_url}/{event_id}"
                    yield scrapy.Request(details_url, headers=response.request.headers, callback=self.parse_event_details)

                # อัปเดต last_event_time เพื่อโหลดข้อมูลถัดไป
                self.last_event_time = data['data'][-1]['attributes'].get('event_time_sort')

                # โหลดข้อมูลถัดไปต่อไปเรื่อย ๆ
                next_url = self.get_next_url()
                yield scrapy.Request(next_url, headers=response.request.headers, callback=self.parse)
            else:
                self.logger.info("ไม่มีข้อมูลเพิ่มเติมแล้ว")

        except json.JSONDecodeError:
            self.logger.error("เกิดข้อผิดพลาดในการอ่าน JSON")



    def parse_event_details(self, response):
        try:
            event = json.loads(response.text).get('data', {}).get('attributes', {})
            if not event:
                self.logger.warning("ไม่พบข้อมูล event")
                return

            title = event.get('title', 'ไม่มีชื่อ')
            description = remove_tags(event.get('description', 'ไม่มีคำอธิบาย')).strip()

            title = event.get('title', 'ไม่มีชื่อ')
            # ดึง raw description และ unescape ก่อน → ส่งให้ extract_ticket_info
            raw_description = event.get('description', 'ไม่มีคำอธิบาย')
            clean_description = html.unescape(remove_tags(raw_description)).strip()
            ticket, ticket_price = self.extract_ticket_info(raw_description)  # ใช้ raw
            description = clean_description  # สำหรับบันทึกลงไฟล์

            # 🔁 ถ้าไม่มีราคาใน API และยังไม่มีราคาจาก description → ใช้ raw_price เสริม
            if ticket_price in [[], "", "null"]:
                raw_price = event.get('ticket_price')
                if isinstance(raw_price, str):
                    price_parts = [p.strip() for p in raw_price.split(',') if p.strip()]
                    try:
                        ticket_price = [int(p) for p in price_parts]
                    except ValueError:
                        ticket_price = raw_price
                elif isinstance(raw_price, (int, float)):
                    ticket_price = [int(raw_price)] if raw_price > 0 else None
                else:
                    ticket_price = None

            if ticket_price in [[], "", "null", None] and str(ticket) != "มีค่าเข้าชม":
                ticket = "ไม่มีค่าเข้าชม"


            # ข้อมูลอื่น ๆ
            event_id = response.url.rstrip('/').split("/")[-1]
            facebook_url = event.get('contactor', {}).get('facebook', {}).get('url')
            event_url = facebook_url if facebook_url else f"https://www.thailandexhibition.com/TradeShow/ID/{event_id}"

            start_date = self.format_thai_date(event.get('event_time', [None])[0])
            end_date = self.format_thai_date(event.get('event_time', [None])[-1])
            reliability_score = 2
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            predicted_categories = predict_category(title, description)

            event_data = {
                'title': title,
                'description': description,
                "categories": predicted_categories,
                'start_date': start_date,
                'end_date': end_date,
                'event_slot_time': self.format_time_range(event.get('event_slot_time', [])),
                'location': event.get('place', 'ไม่มีสถานที่'),
                'url': event_url,
                'cover_picture': event.get('cover_img', {}).get('path', 'ไม่มีรูปปก'),
                'ticket': ticket,
                'ticket_price': ticket_price,
                "reliability_score": reliability_score,
                "timestamp": timestamp,
                "status": determine_status(start_date, end_date)
            }

            # กำหนดชื่อไฟล์โดยล้างอักขระพิเศษ
            filename = re.sub(r"[\\/:*?\"<>|]", "_", title) + ".json"
            base_dir = os.path.dirname(os.path.abspath(__file__))
            raw_data_dir = os.path.join(base_dir, "raw_data", "full")
            os.makedirs(raw_data_dir, exist_ok=True)

            filepath = os.path.join(raw_data_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(event_data, f, ensure_ascii=False, indent=4)

            yield event_data

        except json.JSONDecodeError:
            self.logger.error("เกิดข้อผิดพลาดในการอ่าน JSON")


    def format_thai_date(self, date_str):
        """แปลงวันที่จาก 'YYYY-MM-DD' → 'D เดือน ปี' (เช่น 4 กรกฎาคม 2024)"""
        if not date_str:
            return "ไม่ทราบวันที่"

        thai_months = [
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
            "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
        ]

        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            day = date_obj.day
            month = thai_months[date_obj.month - 1]
            year = date_obj.year
            return f"{day} {month} {year}"
        except Exception as e:
            self.logger.warning(f"แปลงวันที่ไม่สำเร็จ: {date_str} - {e}")
            return date_str

    def format_time_range(self, time_list):
        """
        แปลงเวลา ISO เป็นช่วงเวลา เช่น ['2024-06-03T04:00:00.000Z', '2024-06-03T14:00:00.000Z'] → 11:00–21:00 (เวลาไทย)
        ถ้าไม่มีค่าหรือผิดรูปแบบ ให้ return None
        """
        if not isinstance(time_list, list) or len(time_list) != 2:
            return None

        try:
            start_time = datetime.datetime.fromisoformat(time_list[0].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=7)))
            end_time = datetime.datetime.fromisoformat(time_list[1].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=7)))
            return f"{start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}"
        except Exception as e:
            self.logger.warning(f"แปลงเวลาช่วงไม่สำเร็จ: {time_list} - {e}")
            return None

    def extract_ticket_info(self, description_text):
        import html

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
                # ✅ รองรับ 5,900 และ 5900
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

        # ✅ ตัดราคาที่ต่ำกว่ามาก (เช่น 100, 500 ถ้ามี 5900 อยู่)
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


