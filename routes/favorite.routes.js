const express = require('express');
const router = express.Router();
const Favorite = require('../models/Favorite');
const Exhibition = require('../models/Exhibition');
const auth = require('../middlewares/auth'); // middleware ที่ decode JWT
const mongoose = require('mongoose');

// เพิ่ม favorite
router.post('/', auth, async (req, res) => {
  const { exhibition_id } = req.body;
  try {
    if (!mongoose.Types.ObjectId.isValid(exhibition_id)) {
      return res.status(400).json({ error: "Invalid exhibition ID" });
    }
    
    const favorite = new Favorite({
      user_id: req.user.id,
      exhibition_id
    });
    await favorite.save();
    res.status(201).json({ message: 'Added to favorites' });
  } catch (err) {
    if (err.code === 11000) {
      res.status(400).json({ message: 'Already favorited' });
    } else {
        console.error(err);
      res.status(500).json({ message: 'Server error' });
    }
  }
});

// ลบ favorite
router.delete('/:exhibition_id', auth, async (req, res) => {
  const { exhibition_id } = req.params;
  try {
    if (!mongoose.Types.ObjectId.isValid(exhibition_id)) {
      return res.status(400).json({ error: "Invalid exhibition ID" });
    }
    
    await Favorite.findOneAndDelete({
      user_id: req.user.id,
      exhibition_id
    });
    res.status(200).json({ message: 'Removed from favorites' });
  } catch (err) {
    res.status(500).json({ message: 'Server error' });
  }
});

// เช็คว่าถูก fav ไหม
router.get('/check/:exhibition_id', auth, async (req, res) => {
  const { exhibition_id } = req.params;
  if (!mongoose.Types.ObjectId.isValid(exhibition_id)) {
    return res.status(400).json({ error: "Invalid exhibition ID" });
  }

  const fav = await Favorite.findOne({
    user_id: req.user.id,
    exhibition_id
  });
  res.json({ favorited: !!fav });
});

// ดึงรายการทั้งหมดที่ fav ไว้
router.get('/', auth, async (req, res) => {
  try {
    const favorites = await Favorite.find({ user_id: new mongoose.Types.ObjectId(req.user.id) })
      .populate('exhibition_id');

    // ✅ กรองรายการที่ไม่มีนิทรรศการ (อาจโดนลบไปแล้ว)
    const validFavorites = favorites.filter(f => f.exhibition_id !== null);

    res.json(validFavorites);
  } catch (err) {
    console.error("❌ error:", err);
    res.status(500).json({ message: 'Server error' });
  }
});



module.exports = router;
