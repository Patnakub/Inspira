const cron = require("node-cron");
const mongoose = require("mongoose");
const Exhibition = require("../models/Exhibition");
const Favorite = require("../models/Favorite");
const User = require("../models/User");
const NotificationLog = require("../models/NotificationLog");
const nodemailer = require("nodemailer");
const dayjs = require("dayjs");

// ✅ เชื่อม MongoDB (ชั่วคราวแบบ hardcoded)
const MONGO_URI = "mongodb+srv://inspiraproject2025:ypLEu0xL3plfo2AW@exhibition-cluster.ty3ugcy.mongodb.net/exhibition_db";
mongoose.connect(MONGO_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true,
}).then(() => {
  console.log("✅ Connected to MongoDB");
}).catch((err) => {
  console.error("❌ MongoDB connection error:", err);
});

// ⚙️ แปลงวันที่ภาษาไทย → ISO
const thaiMonths = {
  'มกราคม': '01', 'กุมภาพันธ์': '02', 'มีนาคม': '03', 'เมษายน': '04',
  'พฤษภาคม': '05', 'มิถุนายน': '06', 'กรกฎาคม': '07', 'สิงหาคม': '08',
  'กันยายน': '09', 'ตุลาคม': '10', 'พฤศจิกายน': '11', 'ธันวาคม': '12'
};

function parseThaiDateToISO(str) {
  if (dayjs(str, "YYYY-MM-DD", true).isValid()) {
    return str;
  }

  const match = str?.match(/(\d{1,2}) ([ก-๙]+) (\d{4})/);
  if (!match) return null;
  const [_, d, m, y] = match;
  const mm = thaiMonths[m];
  if (!mm) return null;
  return `${y}-${mm}-${d.padStart(2, "0")}`;
}

// 📧 ตั้งค่า SMTP
const transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: process.env.EMAIL_USERNAME,
    pass: process.env.EMAIL_PASSWORD,
  },
});

async function sendEmail(to, subject, text) {
  await transporter.sendMail({
    from: `"นิทรรศการแจ้งเตือน" <${process.env.EMAIL_USERNAME}>`,
    to,
    subject,
    text,
  });
}

// 🔔 ตรวจสอบนิทรรศการใกล้จบ
async function notifyEndingSoon() {
  const today = dayjs();
  const threeDaysLater = today.add(3, "day");
  const exhibitions = await Exhibition.find({ end_date: { $exists: true } });

  for (const ex of exhibitions) {
    const isoEndDate = parseThaiDateToISO(ex.end_date);
    if (!isoEndDate) continue;

    const endDate = dayjs(isoEndDate);
    if (!endDate.isValid() || endDate.isAfter(threeDaysLater)) continue;

    const formattedDate = endDate.format("D MMMM YYYY");
    const favUsers = await Favorite.find({ exhibition_id: ex._id }).distinct("user_id");

    for (const userId of favUsers) {
      const user = await User.findById(userId);
      if (!user || !user.email) continue;

      const alreadySent = await NotificationLog.findOne({
        user_id: new mongoose.Types.ObjectId(userId),
        exhibition_id: new mongoose.Types.ObjectId(ex._id),
      });
      if (alreadySent) continue;

      const msg = `📅 แจ้งเตือน: นิทรรศการ "${ex.title}" ที่คุณบันทึกไว้ในรายการโปรด กำลังจะจบในวันที่ ${formattedDate}\n\nดูรายละเอียดเพิ่มเติม:\n${process.env.BASE_URL}/exhibition.html?id=${ex._id}`;

      try {
        await sendEmail(user.email, `แจ้งเตือน: นิทรรศการใกล้จบ`, msg);
        await NotificationLog.create({ user_id: userId, exhibition_id: ex._id });
        console.log(`📧 ส่งให้ ${user.email} | ${ex.title}`);
      } catch (err) {
        console.error(`❌ ส่งอีเมลล้มเหลวให้ ${user.email}`, err);
      }
    }
  }
}

// 🔁 สำหรับทดสอบ: เรียกทันทีเมื่อรัน
notifyEndingSoon();
