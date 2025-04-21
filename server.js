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
  'http://127.0.0.1:5000'
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
mongoose.connect(process.env.MONGO_URI)
  .then(() => {
    console.log('✅ Connected to MongoDB');
    syncExhibitionsToElasticsearch(); // ดึงข้อมูลนิทรรศการทั้งหมดไปใส่ Elasticsearch
  })
  .catch(err => console.error('❌ MongoDB connection error:', err));

// 🔁 เรียกใช้ cron แจ้งเตือนนิทรรศการใกล้จบ
require('./cron/notifyEndingExhibitions');


// ✅ Mount routes
app.use('/auth', authRoutes);
app.use('/admin', adminRoutes);
app.use('/categories', categoryRoutes);
app.use('/exhibitions', exhibitionRoutes);
app.use('/favorites', favoriteRoutes);
app.use('/reviews', reviewRoutes);
app.use('/bus-routes', routeRoutes);
app.use('/suggestions', suggestionRoutes);

// ✅ Static page routes (login, verify, admin, etc.)
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'login.html'));
});

app.get('/verify_success', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'verify_success.html'));
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
