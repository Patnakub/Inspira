require("dotenv").config();

const mongoose = require("mongoose");
const connectDB = require("../db");
const Exhibition = require("../models/Exhibition");
const Favorite = require("../models/Favorite");
const User = require("../models/User");
const NotificationLog = require("../models/NotificationLog");
const nodemailer = require("nodemailer");
const dayjs = require("dayjs");
const fs = require("fs");

// ✅ Gmail SMTP
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

// 🔔 ฟังก์ชันหลัก
async function notifyEndingSoon() {
  await connectDB();
  console.log("✅ Connected to MongoDB");

  const today = dayjs();
  const threeDaysLater = today.add(3, "day");

  console.log("📌 กำลังดึงรายการ Favorite...");
  const favorites = await Favorite.find({});

  for (const fav of favorites) {
    const user = await User.findById(fav.user_id);
    if (!user || !user.email) {
      console.log("⚠️ ข้าม: user ไม่มีอีเมลหรือไม่พบ", fav.user_id);
      continue;
    }

    const ex = await Exhibition.findById(fav.exhibition_id);
    if (!ex || !ex.end_date_obj) {
      console.log("⚠️ ข้าม: ไม่พบงานหรือไม่มี end_date_obj:", fav.exhibition_id);
      continue;
    }

    const endDate = dayjs(ex.end_date_obj);
    if (!endDate.isValid()) {
      console.log("⚠️ ข้าม: end_date_obj ไม่ valid:", ex.title);
      continue;
    }

    if (endDate.isAfter(threeDaysLater)) {
      console.log("⚠️ ข้าม: งานยังไม่ใกล้จบ:", ex.title, endDate.format("YYYY-MM-DD"));
      continue;
    }

    const alreadySent = await NotificationLog.findOne({
      user_id: user._id,
      exhibition_id: ex._id,
    });
    if (alreadySent) {
      console.log("📭 ข้าม: เคยแจ้งแล้ว:", ex.title, "|", user.email);
      continue;
    }

    const formattedDate = endDate.format("D MMMM YYYY");
    const msg = `📅 แจ้งเตือน: นิทรรศการ "${ex.title}" ที่คุณบันทึกไว้ในรายการโปรด กำลังจะจบในวันที่ ${formattedDate}\n\nดูรายละเอียดเพิ่มเติม:\n${process.env.BASE_URL}/exhibition.html?id=${ex._id}`;

    try {
      await sendEmail(user.email, `แจ้งเตือน: นิทรรศการใกล้จบ`, msg);
      await NotificationLog.create({ user_id: user._id, exhibition_id: ex._id });
      console.log(`📧 ส่งให้ ${user.email} | ${ex.title}`);
    } catch (err) {
      console.error(`❌ ส่งอีเมลล้มเหลวให้ ${user.email}`, err);
    }
  }

  fs.appendFileSync("notify_log.txt", `✅ แจ้งเตือนเมื่อ ${new Date().toISOString()}\n`);
}

// ▶️ เรียกฟังก์ชัน
notifyEndingSoon();
