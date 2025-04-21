// models/NotificationLog.js
const mongoose = require('mongoose');

const notificationLogSchema = new mongoose.Schema({
  user_id: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  exhibition_id: { type: mongoose.Schema.Types.ObjectId, ref: 'Exhibition', required: true },
  sent_at: { type: Date, default: Date.now }
});

// 1 คน 1 งาน ส่งได้ครั้งเดียว
notificationLogSchema.index({ user_id: 1, exhibition_id: 1 }, { unique: true });

module.exports = mongoose.model('NotificationLog', notificationLogSchema);
