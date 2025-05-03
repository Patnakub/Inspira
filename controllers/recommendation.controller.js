const Recommendation = require('../models/Recommendation');
const Exhibition = require('../models/Exhibition');

const getUserRecommendations = async (req, res) => {
  const userId = req.params.userId;

  try {
    const userRec = await Recommendation.findOne({ user_id: userId });
    if (!userRec) return res.status(404).json({ message: 'ไม่พบคำแนะนำของผู้ใช้คนนี้' });

    const top10 = userRec.recommendations
      .sort((a, b) => b.score - a.score)
      .slice(0, 20); // เผื่อบางงานถูกกรองออก (เกิน 10 ไว้ก่อน)

    const exhibitionIds = top10.map(r => r.event_id);

    const exhibitions = await Exhibition.find({
      _id: { $in: exhibitionIds },
      status: { $in: ['ongoing', 'upcoming'] }
    });

    // แมปตามลำดับ score เดิม
    const sorted = top10
      .map(rec => exhibitions.find(ex => ex._id.toString() === rec.event_id))
      .filter(Boolean) // กรอง null (กรณี event ถูกลบหรือ status เป็น past)
      .slice(0, 10);    // แสดงจริงแค่ 10

    res.json(sorted);

  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'เกิดข้อผิดพลาดในการโหลดคำแนะนำ' });
  }
};

module.exports = { getUserRecommendations };
