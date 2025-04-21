const express = require('express');
const router = express.Router();
const multer = require('multer');
const auth = require('../middlewares/auth');
const Review = require('../models/Review');
const path = require('path');
const mongoose = require('mongoose');
const Exhibition = require('../models/Exhibition'); 


// 🖼️ ตั้งค่าที่เก็บไฟล์
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, 'public/uploads/reviews'),
  filename: (req, file, cb) => {
    const unique = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, unique + path.extname(file.originalname));
  }
});
const upload = multer({ storage });

// ✅ แก้ POST /reviews
router.post('/', auth, upload.single('image'), async (req, res) => {
    try {
      const { exhibition_id, rating, review } = req.body;

      if (!mongoose.Types.ObjectId.isValid(exhibition_id)) {
        return res.status(400).json({ error: "Invalid exhibition ID" });
      }
  
      const image_url = req.file
        ? `/uploads/reviews/${req.file.filename}`
        : null;

      // ดึงข้อมูลนิทรรศการเพื่อเช็คสถานะ
      const exhibition = await Exhibition.findById(exhibition_id);
      if (!exhibition) return res.status(404).json({ error: 'Exhibition not found' });

      if (exhibition.status === 'upcoming') {
        return res.status(403).json({ error: 'ยังไม่สามารถรีวิวได้ในขณะนี้' });
      }
  
      // 🔍 ตรวจสอบว่ามีรีวิวเดิมไหม
      let existingReview = await Review.findOne({
        user_id: req.user.id,
        exhibition_id
      }).sort({ updated_at: -1 });
      

      if (existingReview) {
        // 👇 ถ้ามี: ให้ update
        existingReview.rating = rating;
        existingReview.review = review;
        existingReview.updated_at = new Date();
        if (image_url) {
          existingReview.image_url = image_url;
        }
        await existingReview.save();
        return res.json({ message: 'แก้ไขรีวิวสำเร็จ', review: existingReview });
      }
  
      // 👇 ถ้าไม่มี: สร้างใหม่
      const newReview = new Review({
        user_id: req.user.id,
        exhibition_id,
        rating,
        review,
        image_url,
      });
  
      await newReview.save();
      res.json({ message: 'รีวิวสำเร็จ', review: newReview });
    } catch (err) {
      console.error('Error creating review:', err);
      res.status(500).json({ error: 'Server error' });
    }
  });
  

// ✅ แก้ GET /reviews/:exhibitionId
router.get('/:exhibitionId', async (req, res) => {
    try {
      const id = req.params.exhibitionId;

      if (!mongoose.Types.ObjectId.isValid(id)) {
        return res.status(400).json({ error: "Invalid exhibition ID" });
      }
        const reviews = await Review.aggregate([
            { $match: { exhibition_id: new mongoose.Types.ObjectId(req.params.exhibitionId) } },
            { $sort: { updatedAt: -1 } }, // ตรวจสอบว่าเรียงตาม `updatedAt` ถูกต้อง
            {
              $group: {
                _id: "$user_id",
                doc: { $first: "$$ROOT" }
              }
            },
            { $replaceRoot: { newRoot: "$doc" } }
          ]);
          
      // เติมข้อมูล user ด้วย populate แบบ manual (เพราะ aggregate ใช้ populate ไม่ได้)
      const populated = await Review.populate(reviews, { path: "user_id", select: "username" });
  
      res.json(populated);
    } catch (err) {
      console.error('Error fetching reviews:', err);
      res.status(500).json({ error: 'Server error' });
    }
  });
  

// ✅ GET /reviews/my (ดึงเฉพาะของ user คนปัจจุบัน)
router.get('/me/all', auth, async (req, res) => {
  try {
    const myReviews = await Review.find({ user_id: req.user.id })
      .populate('exhibition_id', 'title location start_date end_date cover_picture');

    res.json(myReviews);
  } catch (err) {
    console.error('Error fetching my reviews:', err);
    res.status(500).json({ error: 'Server error' });
  }
});

// ✅ PUT /reviews/:id
router.put('/:id', auth, upload.single('image'), async (req, res) => {
    try {
      const reviewId = req.params.id;
      if (!mongoose.Types.ObjectId.isValid(reviewId)) {
        return res.status(400).json({ error: "Invalid review ID" });
      }

      const review = await Review.findOne({ _id: req.params.id, user_id: req.user.id });
      if (!review) return res.status(404).json({ error: "ไม่พบรีวิวของคุณ" });

      // ดึงข้อมูลนิทรรศการเพื่อเช็คสถานะ
      const exhibition = await Exhibition.findById(review.exhibition_id);
      if (!exhibition) return res.status(404).json({ error: 'Exhibition not found' });

      if (exhibition.status === 'upcoming') {
        return res.status(403).json({ error: 'ยังไม่สามารถรีวิวได้ในขณะนี้' });
      }

      const { rating, review: text } = req.body;
  
      review.rating = rating;
      review.review = text;
      review.updated_at = new Date();
  
      if (req.file) {
        review.image_url = `/uploads/reviews/${req.file.filename}`;
      }
  
      await review.save();
      res.json({ message: "แก้ไขรีวิวเรียบร้อย", review });
    } catch (err) {
      console.error('Error updating review:', err);
      res.status(500).json({ error: 'Server error' });
    }
  });
  
// GET /reviews/id/:id
router.get('/id/:id', async (req, res) => {
    try {
      const id = req.params.id;
      if (!mongoose.Types.ObjectId.isValid(id)) {
        return res.status(400).json({ error: "Invalid review ID" });
      }

      const review = await Review.findById(req.params.id);
      if (!review) return res.status(404).json({ message: 'Review not found' });
      res.json(review);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });
  
  
module.exports = router;
