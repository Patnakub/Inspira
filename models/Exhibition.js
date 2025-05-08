// sync mongoose -> elasticsearch
const mongoose = require('mongoose');
const { syncExhibitionToElastic } = require('../utils/elasticSync');

const ExhibitionSchema = new mongoose.Schema({
  title: String,
  description: String,
  location: String,
  start_date: String,        
  end_date: String,      
  start_date_obj: Date,
  end_date_obj: Date,        
  categories: [String],
  event_slot_time: String,
  ticket: String,
  ticket_price: {
    type: mongoose.Schema.Types.Mixed,
    default: null
  },
  url: String,
  cover_picture: String,
  image: String,
  latitude: {
    type: Number
  },
  longitude: {
    type: Number
  },
  category_verified: { type: Boolean, default: false }
  
});

ExhibitionSchema.post('save', function () {
  trySyncToElastic(this);
});

ExhibitionSchema.post('findOneAndUpdate', function (doc) {
  if (doc) trySyncToElastic(doc);
});

ExhibitionSchema.index({ start_date_obj: 1 });
ExhibitionSchema.index({ end_date_obj: 1 });

function trySyncToElastic(doc) {
  if (!process.env.SKIP_ELASTIC_SYNC && process.env.ELASTIC_NODE) {
    const { syncExhibitionToElastic } = require('../utils/elasticSync');
    syncExhibitionToElastic(doc);
  } else {
    console.warn("⚠️ SKIP_ELASTIC_SYNC is set or ELASTIC_NODE missing — skipping sync.");
  }
}

module.exports = mongoose.model('Exhibition', ExhibitionSchema);
