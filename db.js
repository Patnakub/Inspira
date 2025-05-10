// db.js
const mongoose = require('mongoose');
require('dotenv').config({ path: require('path').resolve(__dirname, '.env') });
let isConnected = false;

const connectDB = async () => {
  if (isConnected) return;
  try {
    console.log("⛳ MONGODB_URI =", process.env.MONGODB_URI);
    await mongoose.connect(process.env.MONGODB_URI);
    isConnected = true;
    console.log('✅ Connected to MongoDB');
  } catch (err) {
    console.error('❌ MongoDB connection error:', err);
  }
};

module.exports = connectDB;
