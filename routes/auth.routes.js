const express = require('express');
const router = express.Router();
const auth = require('../middlewares/auth');
const { getMe } = require('../controllers/auth.controller');
const { register, login, requestReset, confirmReset, resendVerification, verifyEmail, changePassword, checkDuplicate,checkSession } = require('../controllers/auth.controller');

// สมัครสมาชิก
router.post('/register', register);

// ✅ ยืนยัน email
router.get('/verify-email', verifyEmail);

// ✅ ส่ง email อีกครั้ง
router.post('/resend-verification', resendVerification);

// Login API
router.post('/login', login);

// ✅ ขอ PIN
router.post('/request-reset', requestReset);    

// ✅ ยืนยัน PIN + ตั้งรหัสใหม่
router.post('/confirm-reset', confirmReset);     

// ✅ ตั้งรหัสใหม่
router.post('/change-password', auth, changePassword);

// ✅ สำหรับ Admin
router.get('/me', auth, getMe);

// ✅ ตรวจข้อมูลซ้ำ
router.post('/check-duplicate', checkDuplicate);

// ✅ ตรวจ login
router.get('/session', checkSession);

module.exports = router;
