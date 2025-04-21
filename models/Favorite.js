const mongoose = require('mongoose');

const favoriteSchema = new mongoose.Schema({
  user_id: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  exhibition_id: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Exhibition',
    required: true
  },
  created_at: {
    type: Date,
    default: () => new Date()
  }
});

// ไม่ให้ fav ซ้ำได้ (1 คน fav นิทรรศการเดียวกันได้แค่ครั้งเดียว)
favoriteSchema.index({ user_id: 1, exhibition_id: 1 }, { unique: true });

module.exports = mongoose.model('Favorite', favoriteSchema);
