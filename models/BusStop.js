const mongoose = require('mongoose');

const busStopSchema = new mongoose.Schema({
  stop_id: String,
  stop_name: String,
  latitude: Number,
  longitude: Number,
  routes: [
    {
      route_id: String,
      short_name: String,
      long_name: String
    }
  ],
  min_price: Number,
  max_price: Number
});

module.exports = mongoose.model('BusStop', busStopSchema, 'bus'); 
// 'bus' คือชื่อ collection ที่คุณใช้ใน MongoDB
