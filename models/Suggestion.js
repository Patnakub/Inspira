const mongoose = require("mongoose");

const SuggestionSchema = new mongoose.Schema({
  title: { type: String, required: true },
  location: { type: String, required: true },
  start_date: { type: String, required: true },
  end_date: { type: String },                       // วันที่สิ้นสุด
  event_slot_time: { type: String },                // เวลาเริ่มกิจกรรม
  categories: { type: [String], default: [] },      // หมวดหมู่ที่เลือกได้หลายหมวด
  description: { type: String, required: true },
  ticket: { type: String, default: "ไม่ระบุ" },
  ticket_price: { type: [Number], default: [] },
  image_url: { type: String, required: true },
  status: { type: String, default: "pending" },     // pending, approved, rejected
  timestamp: { type: Date, default: Date.now },     // เวลาที่สร้างเอกสาร
  reliability_score: { type: Number, default: 1 },  // คะแนนความน่าเชื่อถือ
  latitude: { type: Number, default: null },
  longitude: { type: Number, default: null },
  created_at: { type: Date, default: Date.now }
});

module.exports = mongoose.model("Suggestion", SuggestionSchema);
