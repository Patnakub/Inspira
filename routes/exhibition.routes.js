const express = require('express');
const router = express.Router();
const exhibitionController = require('../controllers/exhibition.controller');
const normalizeExhibitionData = require('../middlewares/normalizeExhibitionData');

// 🧭 ดึงนิทรรศการทั้งหมดแบบกรอง
router.get('/', exhibitionController.getFilteredExhibitions);

// 🔍 ค้นหาจากคีย์เวิร์ด
router.get('/search', exhibitionController.searchExhibitions);

// ✅ Ongoing / Upcoming
router.get('/ongoing', exhibitionController.getOngoingExhibitions);
router.get('/upcoming', exhibitionController.getUpcomingExhibitions);

// ✅ ดึงข้อมูลป้ายรถเมล์ตามนิทรรศการ
router.get('/:id/nearby-bus', exhibitionController.getNearbyBusStops);

// ✅ ดึงนิทรรศการตาม ID พร้อม normalize
router.get('/:id', normalizeExhibitionData, exhibitionController.getExhibitionById);



module.exports = router;
