const mongoose = require('mongoose');

const recommendationSchema = new mongoose.Schema({
  user_id: {
    type: String,
    required: true,
    index: true
  },
  recommendations: [
    {
      event_id: String,
      score: Number
    }
  ],
  updated_at: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('Recommendation', recommendationSchema);
