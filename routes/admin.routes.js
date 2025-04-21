// routes/admin.routes.js
const express = require('express');
const router = express.Router();
const auth = require('../middlewares/auth');
const checkAdmin = require('../middlewares/checkAdmin');
const adminController = require('../controllers/admin.controller');

// ตรวจสอบ token + สิทธิ์ admin ทุกครั้ง
router.get('/suggestions/pending', auth, checkAdmin, adminController.getPendingSuggestions);
router.put('/suggestions/:id/approve', auth, checkAdmin, adminController.approveSuggestion);
router.delete('/suggestions/:id', auth, checkAdmin, adminController.deleteSuggestion);
router.put('/suggestions/:id/category', auth, checkAdmin, adminController.updateCategory);
router.put('/exhibitions/:id/category', auth, checkAdmin, adminController.updateExhibitionCategory);
router.get('/exhibitions/others', auth, checkAdmin, adminController.getOthersExhibitions);
router.put('/exhibitions/:id/confirm-others', auth, checkAdmin, adminController.confirmOthersCategory);


module.exports = router;
