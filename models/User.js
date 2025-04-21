const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true,
    minlength: 4,
    maxlength: 20,
    match: /^[a-zA-Z0-9_]+$/, // อนุญาต a-z A-Z 0-9 _
  },
  password: {
    type: String,
    required: true,
    minlength: 4, // ควรใช้ >= 6 จริงๆ ถ้าเข้ารหัสแล้วไม่มีผล
  },
  email: {
    type: String,
    required: true,
    unique: true,
    match: /^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$/ // รูปแบบอีเมล
  },
  gender: {
    type: String,
    required: true,
    enum: ['male', 'female'] // รับแค่ male หรือ female
  },
  birthdate: {
    type: Date,
    required: true,
    validate: {
      validator: function (value) {
        const today = new Date();
        return value < today; // วันเกิดต้องไม่ใช่อนาคต
      },
      message: 'Birthdate must be in the past'
    }
  },
  interests: {
    type: [String],
    required: true,
    validate: {
      validator: function (arr) {
        return arr.length > 0 && arr.length <= 3;
      },
      message: 'You must select 1 to 3 interests'
    }
  },
  created_at: {
    type: Date,
    required: true,
    default: () => new Date()
  },
  updated_at: {
    type: Date,
    required: true,
    default: () => new Date()
  },
  resetPin: {
    type: String
  },
  resetPinExpire: {
    type: Date
  },
  isEmailVerified: {
    type: Boolean,
    required: true,
    default: false
  },
  verifyToken: {
    type: String
  },
  verifyTokenExpire: {
    type: Date
  },
  role: {
    type: String,
    enum: ['user', 'admin'],
    default: 'user',  // default คือ user
  },
  
});

module.exports = mongoose.model('User', userSchema);
