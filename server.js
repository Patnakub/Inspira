const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();
const path = require('path');
const syncExhibitionsToElasticsearch = require('./utils/syncToElasticsearch');


// 🔧 Import routes
const favoriteRoutes = require('./routes/favorite.routes');
const reviewRoutes = require('./routes/review.routes');
const routeRoutes = require('./routes/route.routes');
const suggestionRoutes = require("./routes/suggestion.routes");
const adminRoutes = require('./routes/admin.routes');
const authRoutes = require('./routes/auth.routes');
const categoryRoutes = require('./routes/category.routes');
const exhibitionRoutes = require('./routes/exhibition.routes');
const NotificationLog = require('./models/NotificationLog');


// ✅ Init app
const app = express();

// ✅ CORS setup
const allowedOrigins = [
  'http://localhost:3000',
  'http://127.0.0.1:5500',
  'http://localhost:5500',
  'http://localhost:5000',
  'http://127.0.0.1:5000',
  'https://inspirafe123.ap.ngrok.io',
  'https://exhibitionapi123.ap.ngrok.io'
];

app.use(cors({
  origin: function (origin, callback) {
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      console.warn(`❌ Blocked by CORS: ${origin}`);
      callback(new Error('Not allowed by CORS'));
    }
  },
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
}));

// ✅ Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));
app.use('/uploads', express.static(path.join(__dirname, 'public/uploads')));

// ✅ Connect MongoDB
const connectDB = require('./db');

connectDB().then(() => {
  syncExhibitionsToElasticsearch();
});

// ✅ Mount routes
app.use('/auth', authRoutes);
app.use('/admin', adminRoutes);
app.use('/categories', categoryRoutes);
app.use('/exhibitions', exhibitionRoutes);
app.use('/favorites', favoriteRoutes);
app.use('/reviews', reviewRoutes);
app.use('/bus-routes', routeRoutes);
app.use('/suggestions', suggestionRoutes);
app.use('/recommendations', require('./routes/recommendation.routes'));



// ✅ Static page routes (login, verify, admin, etc.)
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'login.html'));
});

app.get('/verify_success', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'verify_success.html'));
});

// ✅ เพิ่มส่วนนี้หลังจากบรรทัดด้านบน
app.get('/verify-email', async (req, res) => {
  const { token } = req.query;
  
  if (!token) {
    return res.status(400).send(`
      <!DOCTYPE html>
      <html><head><title>Error</title></head>
      <body style="font-family: sans-serif; text-align: center; margin-top: 100px;">
        <h2>❌ ลิงก์ไม่ถูกต้อง</h2>
        <p>กรุณาตรวจสอบลิงก์ในอีเมลอีกครั้ง</p>
        <a href="/login.html">กลับไปหน้า Login</a>
      </body></html>
    `);
  }

  try {
    const User = require('./models/User');
    
    const user = await User.findOne({
      verifyToken: token,
      verifyTokenExpire: { $gt: new Date() }
    });

    if (!user) {
      return res.status(400).send(`
        <!DOCTYPE html>
        <html><head><title>Token หมดอายุ</title></head>
        <body style="font-family: sans-serif; text-align: center; margin-top: 100px;">
          <h2>❌ ลิงก์หมดอายุหรือไม่ถูกต้อง</h2>
          <p>กรุณาสมัครสมาชิกใหม่หรือขออีเมลยืนยันใหม่</p>
          <a href="/register.html">สมัครสมาชิกใหม่</a>
        </body></html>
      `);
    }

    // อัพเดตสถานะผู้ใช้
    user.isEmailVerified = true;
    user.verifyToken = null;
    user.verifyTokenExpire = null;
    await user.save();

    // แสดงหน้าสำเร็จ
    res.send(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>ยืนยันอีเมลสำเร็จ</title>
        <style>
          body { 
            font-family: sans-serif; 
            text-align: center; 
            margin-top: 100px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
          }
          .container {
            background: white;
            color: #333;
            padding: 40px;
            border-radius: 10px;
            max-width: 400px;
            margin: 0 auto;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
          }
          .success-icon { font-size: 60px; margin-bottom: 20px; }
          .btn {
            background: #4CAF50;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 5px;
            display: inline-block;
            margin-top: 20px;
          }
          .btn:hover { background: #45a049; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="success-icon">✅</div>
          <h2>ยืนยันอีเมลสำเร็จ!</h2>
          <p>ขอบคุณ <strong>${user.username}</strong><br>
          คุณสามารถเข้าสู่ระบบได้แล้ว</p>
          <a href="/login.html" class="btn">เข้าสู่ระบบ</a>
        </div>
      </body>
      </html>
    `);

  } catch (err) {
    console.error('❌ Email verification error:', err);
    res.status(500).send(`
      <!DOCTYPE html>
      <html><head><title>เกิดข้อผิดพลาด</title></head>
      <body style="font-family: sans-serif; text-align: center; margin-top: 100px;">
        <h2>❌ เกิดข้อผิดพลาดในระบบ</h2>
        <p>กรุณาลองใหม่อีกครั้งหรือติดต่อผู้ดูแลระบบ</p>
        <a href="/register.html">กลับไปหน้าสมัครสมาชิก</a>
      </body></html>
    `);
  }
});

// ✅ Serve all .html pages in /public dynamically
app.get('/:file', (req, res, next) => {
  const file = req.params.file;
  if (file.endsWith('.html')) {
    res.sendFile(path.join(__dirname, 'public', file));
  } else {
    next();
  }
});

// ✅ 404 fallback
app.use((req, res) => {
  res.status(404).sendFile(path.join(__dirname, 'public', '404.html'));
});

// ✅ Start server
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`🚀 Server is running at http://localhost:${PORT}`);
});
