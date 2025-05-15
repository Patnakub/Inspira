const Exhibition = require("../models/Exhibition");
const { getLatLonWithFallback } = require("../utils/locationUtils");
const mongoose = require("mongoose");


function cleanUrl(badUrl) {
  if (!badUrl || typeof badUrl !== "string") return null;

  badUrl = badUrl.trim()
    .replace(/wwwhttps/g, "https:")
    .replace(/https?:\/\/https?:\/\//g, "https://");

  const match = badUrl.match(/https?:\/\/[^\s"']+/);
  if (!match) return null;

  let cleaned = match[0];

  if (cleaned.includes("facebook.com")) {
    try {
      const urlObj = new URL(cleaned);
      const parts = urlObj.pathname.split('/').filter(Boolean);
      let username = parts[0] || "";
      username = username.split('.')[0];
      return `https://www.facebook.com/${username}`;
    } catch (err) {
      const matchUsername = cleaned.match(/facebook\.com\/([a-zA-Z0-9._\-]+)/);
      if (matchUsername) {
        const username = matchUsername[1].split('.')[0];
        return `https://www.facebook.com/${username}`;
      }
      return "https://www.facebook.com";
    }
  }

  return cleaned;
}

function formatDescriptionToList(text) {
  if (!text || typeof text !== "string") return "";

  // ล้างข้อมูลเบื้องต้น
  text = text
    .replace(/\r?\n|\r/g, " ")          // แทน \n หรือ \r ด้วยช่องว่าง
    .replace(/\xa0/g, " ")              // แทน &nbsp;
    .replace(/<[^>]+>/g, "")            // ลบแท็ก HTML
    .replace(/\s\s+/g, " ")             // ลบช่องว่างซ้ำซ้อน
    .trim();

  // แยกส่วนที่เป็น bullet (•)
  const parts = text.split(/•\s*/).filter(part => part.trim() !== "");

  if (parts.length <= 1) {
    // ไม่มี bullet — คืนข้อความเป็น paragraph เดียว
    return `<p>${text}</p>`;
  }

  const paragraph = parts[0];                 // ย่อหน้าแรกก่อน bullet
  const bullets = parts.slice(1);             // หัวข้อรายการ

  return `<p>${paragraph}</p>
    <ul class="list-disc pl-6 space-y-1">
      ${bullets.map(item => `<li>${item.trim()}</li>`).join("\n")}
    </ul>`;
}

function extractTimeFromDescription(desc) {
  if (!desc || typeof desc !== "string") return null;

  // ตัวอย่าง: เวลา 10.00 - 18.00 น.
  const pattern1 = /เวลา\s*(\d{1,2}[:.]\d{2})\s*[-–]\s*(\d{1,2}[:.]\d{2})/i;

  // ตัวอย่าง: ตั้งแต่ 17:00 น. ถึง 20:00 น.
  const pattern2 = /ตั้งแต่\s*(\d{1,2}[:.]\d{2})\s*(?:น\.|น|โมง)?\s*ถึง\s*(\d{1,2}[:.]\d{2})/i;

  let match = desc.match(pattern1);
  if (match) {
    return `${match[1].replace('.', ':')} - ${match[2].replace('.', ':')}`;
  }

  match = desc.match(pattern2);
  if (match) {
    return `${match[1].replace('.', ':')} - ${match[2].replace('.', ':')}`;
  }

  return null;
}


module.exports = async function normalizeExhibitionData(req, res, next) {
  try {
    const { id } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ message: "Invalid exhibition ID" });}
    
    const exhibition = await Exhibition.findById(req.params.id);
    if (!exhibition) return res.status(404).json({ message: "Exhibition not found" });

    // ✅ เติมพิกัดถ้ายังไม่มี (โดย fallback ไปแปลงจาก location)
    if (!exhibition.latitude || !exhibition.longitude) {
      const coords = await getLatLonWithFallback(exhibition.location);

      if (coords) {
        exhibition.latitude = coords.lat;
        exhibition.longitude = coords.lon;
        await exhibition.save();
      } else {
        console.warn("⚠️ ไม่สามารถหา coordinates ได้สำหรับ:", exhibition.title);
        // อย่าตัด request ทิ้ง — ปล่อยให้ผ่านต่อไป
      }
    }


    // ✅ ผูกไว้ให้ controller ใช้งาน
    req.exhibition = exhibition;

    // ✅ ดัก res.json แล้ว format ค่า
    const originalJson = res.json;
    res.json = function (data) {
      if (data) {
        if (data.ticket_price != null && !Array.isArray(data.ticket_price)) {
          data.ticket_price = [data.ticket_price];
        }

        if (data.url) {
          data.url = cleanUrl(data.url);
        }

        if (data.description) {
          data.description = formatDescriptionToList(data.description);
        }

        if (!data.event_slot_time && data.description) {
          const extractedTime = extractTimeFromDescription(data.description);
          if (extractedTime) {
            data.event_slot_time = extractedTime;
          }
        }
      }
      originalJson.call(this, data);
    };

    next();
  } catch (err) {
    console.error("❌ normalizeExhibitionData error:", err);
    res.status(500).json({ message: "Internal server error" });
  }
};
