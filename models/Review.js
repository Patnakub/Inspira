const mongoose = require('mongoose');

const reviewSchema = new mongoose.Schema({
  user_id: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  exhibition_id: { type: mongoose.Schema.Types.ObjectId, ref: 'Exhibition', required: true },
  rating: { type: Number, min: 1, max: 5, required: true },
  review: { type: String },
  image_url: { type: String },
}, { timestamps: true }); 


module.exports = mongoose.model('Review', reviewSchema);
