// controllers/admin.controller.js
const Suggestion = require('../models/Suggestion');
const Exhibition = require('../models/Exhibition');

exports.getPendingSuggestions = async (req, res) => {
  try {
    const suggestions = await Suggestion.find({ status: 'pending' });
    res.json(suggestions);
  } catch (err) {
    res.status(500).json({ msg: 'เกิดข้อผิดพลาดในการดึงรายการ' });
  }
};

exports.approveSuggestion = async (req, res) => {
  try {
    const suggestion = await Suggestion.findById(req.params.id);
    if (!suggestion) return res.status(404).json({ msg: 'ไม่พบรายการ' });

    const now = new Date();
    const start = new Date(suggestion.start_date);
    const end = new Date(suggestion.end_date);

    let status = 'unknown';
    if (start <= now && end >= now) {
      status = 'ongoing';
    } else if (start > now) {
      status = 'upcoming';
    }

    const newExhibition = new Exhibition({
      title: suggestion.title,
      description: suggestion.description,
      location: suggestion.location,
      start_date: suggestion.start_date,
      end_date: suggestion.end_date,
      categories: suggestion.category ? [suggestion.category] : ['Others'],
      event_slot_time: suggestion.event_slot_time,
      ticket: suggestion.ticket,
      ticket_price: suggestion.ticket_price,
      url: suggestion.url,
      cover_picture: suggestion.image_url,
      image: suggestion.image_url,
      latitude: suggestion.lat,
      longitude: suggestion.lon,
      status,
    });

    await newExhibition.save();
    await Suggestion.findByIdAndDelete(suggestion._id);

    res.json({ msg: 'อนุมัติและย้ายข้อมูลเรียบร้อย' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ msg: 'ไม่สามารถอนุมัติได้' });
  }
};

exports.deleteSuggestion = async (req, res) => {
  try {
    const result = await Suggestion.findByIdAndDelete(req.params.id);
    if (!result) return res.status(404).json({ msg: 'ไม่พบรายการ' });
    res.json({ msg: 'ลบรายการเรียบร้อย' });
  } catch (err) {
    res.status(500).json({ msg: 'ไม่สามารถลบได้' });
  }
};

exports.updateCategory = async (req, res) => {
  const { id } = req.params;
  const { category } = req.body;

  try {
    const suggestion = await Suggestion.findById(id);
    if (!suggestion) return res.status(404).json({ message: "ไม่พบงานนิทรรศการ" });

    suggestion.categories = [category];
    await suggestion.save();

    res.json({ message: "อัปเดตหมวดหมู่สำเร็จ" });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: "เกิดข้อผิดพลาด" });
  }
};

exports.getExhibitionsWithOthers = async (req, res) => {
  try {
    const exhibitions = await Exhibition.find({ categories: { $in: ["Others"] } });
    res.json(exhibitions);
  } catch (err) {
    console.error("❌ getExhibitionsWithOthers:", err);
    res.status(500).json({ message: "เกิดข้อผิดพลาดในการดึงข้อมูล" });
  }
};


exports.updateExhibitionCategory = async (req, res) => {
  const { id } = req.params;
  const { category } = req.body;

  try {
    const ex = await Exhibition.findById(id);
    if (!ex) return res.status(404).json({ message: "ไม่พบนิทรรศการ" });

    let updatedCategories = (ex.categories || []).filter(c => c !== "Others");
    if (!updatedCategories.includes(category)) {
      updatedCategories.push(category);
    }

    ex.categories = updatedCategories;
    ex.category_verified = true; 
    await ex.save();

    res.json({ message: "อัปเดตหมวดหมู่สำเร็จ" });
  } catch (err) {
    console.error("❌ updateExhibitionCategory:", err);
    res.status(500).json({ message: "เกิดข้อผิดพลาดในการอัปเดตหมวดหมู่" });
  }
};


exports.getOthersExhibitions = async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const limit = parseInt(req.query.limit) || 10;
  const skip = (page - 1) * limit;

  try {
    const query = { categories: "Others", category_verified: false };

    if (req.query.status && req.query.status !== "all") {
      query.status = req.query.status;
    }

    // ✅ เลือกวิธีเรียงลำดับ
    const sortOption =
      req.query.status === "past" ? { updatedAt: -1 } : { start_date: 1 };

    const total = await Exhibition.countDocuments(query);
    const exhibitions = await Exhibition.find(query)
      .sort(sortOption)
      .skip(skip)
      .limit(limit)
      .lean();

    res.json({ exhibitions, total });
  } catch (err) {
    console.error("❌ getOthersExhibitions error:", err);
    res.status(500).json({ message: "เกิดข้อผิดพลาด" });
  }
};



// ✅ ยืนยันว่า Others ถูกต้อง
exports.confirmOthersCategory = async (req, res) => {
  const { id } = req.params;

  try {
    const exhibition = await Exhibition.findById(id);
    if (!exhibition) return res.status(404).json({ message: "ไม่พบนิทรรศการ" });

    exhibition.category_verified = true;
    await exhibition.save();

    res.json({ message: "ยืนยันหมวดหมู่ Others สำเร็จ" });
  } catch (err) {
    console.error("❌ confirmOthersCategory:", err);
    res.status(500).json({ message: "เกิดข้อผิดพลาดในการยืนยัน" });
  }
};




