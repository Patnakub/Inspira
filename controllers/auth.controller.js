const User = require('../models/User');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const nodemailer = require('nodemailer');
const crypto = require('crypto');

// ✅ ฟังก์ชั่น register
const register = async (req, res) => {
  try {
    const body = req.body;

    const existing = await User.findOne({ username: body.username });
    if (existing) {
      return res.status(400).json({ msg: 'Username already exists' });
    }

    const hashed = await bcrypt.hash(body.password, 10);

    const user = new User({
      username: body.username,
      password: hashed,
      email: body.email,
      gender: body.gender,
      birthdate: body.birthdate,
      interests: body.interests,
      created_at: new Date(),
      updated_at: new Date(),
    });

    // ✅ สร้าง token ยืนยัน
    const token = crypto.randomBytes(32).toString('hex');
    user.verifyToken = token;
    user.verifyTokenExpire = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 ชม.

    await user.save();

    // ✅ ส่งอีเมลยืนยัน
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.EMAIL_USERNAME,
        pass: process.env.EMAIL_PASSWORD,
      },
    });

    const baseUrl = process.env.BASE_URL || "http://localhost:5000";
    const verifyLink = `${baseUrl}/auth/verify-email?token=${token}`;
    const mailOptions = {
      from: process.env.EMAIL_USERNAME,
      to: body.email,
      subject: 'Please verify your email',
      html: `
        <h3>สวัสดี ${body.username}</h3>
        <p>กรุณาคลิกปุ่มด้านล่างเพื่อยืนยันอีเมลของคุณ</p>
        <a href="${verifyLink}" style="display:inline-block;padding:10px 20px;background:#4CAF50;color:white;text-decoration:none;">✅ ยืนยันอีเมล</a>
        <p>หากปุ่มกดไม่ได้ ให้คลิกที่ลิงก์นี้: <br>${verifyLink}</p>
      `,
    };

    await transporter.sendMail(mailOptions);

    res.status(201).json({ msg: 'Registered successfully. Please check your email to verify.' });
  } catch (err) {
    console.error('❌ Register error:', err.message);
    res.status(500).json({ error: err.message });
  }
};


// ✅ ฟังก์ชั่นยืนยัน email
const verifyEmail = async (req, res) => {
  const { token } = req.query;
  try {
    const user = await User.findOne({
      verifyToken: token,
      verifyTokenExpire: { $gt: new Date() }
    });

    if (!user) return res.status(400).send('❌ Invalid or expired token');

    user.isEmailVerified = true;
    user.verifyToken = null;
    user.verifyTokenExpire = null;
    await user.save();

    res.redirect('/verify_success.html'); 
  } catch (err) {
    console.error('Verify error:', err.message);
    res.status(500).send('❌ Server error');
  }
};

// ✅ ฟังก์ชั่นส่งอีเมลอีกครั้ง
const resendVerification = async (req, res) => {
  const { email } = req.body;
  console.log('📬 Request resend for:', email);

  try {
    const user = await User.findOne({ email });
    if (!user) return res.status(404).json({ message: 'Email not found' });
    if (user.isEmailVerified) return res.status(400).json({ message: 'Email already verified' });

    // ✅ Debug
    const token = crypto.randomBytes(32).toString('hex');
    console.log('🧪 New token:', token);

    user.verifyToken = token;
    user.verifyTokenExpire = new Date(Date.now() + 24 * 60 * 60 * 1000);
    await user.save();

    const verifyLink = `http://localhost:5000/auth/verify-email?token=${token}`;
    console.log('🔗 link:', verifyLink);

    const mailOptions = {
      from: process.env.EMAIL_USERNAME,
      to: email,
      subject: 'Please verify your email',
      html: `<h3>คลิกลิงก์เพื่อยืนยัน: <a href="${verifyLink}">ยืนยันอีเมล</a></h3>`
    };

    console.log('📦 email options:', mailOptions);

    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.EMAIL_USERNAME,
        pass: process.env.EMAIL_PASSWORD,
      },
    });

    await transporter.sendMail(mailOptions);
    res.json({ message: 'Verification email sent again.' });
  } catch (err) {
    console.error('❌ Resend error:', err.message);
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
};



// ✅ ฟังก์ชั่น request pin

const requestReset = async (req, res) => {
  const { email } = req.body;

  try {
    const user = await User.findOne({ email });
    if (!user) return res.status(404).json({ message: 'Email not found' });

    const pin = Math.floor(100000 + Math.random() * 900000).toString(); // 6 หลัก
    const expire = new Date(Date.now() + 10 * 60 * 1000); // หมดอายุใน 10 นาที

    user.resetPin = pin;
    user.resetPinExpire = expire;
    await user.save();

    // ส่งอีเมล
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.EMAIL_USERNAME,
        pass: process.env.EMAIL_PASSWORD,
      },
    });

    const mailOptions = {
      from: process.env.EMAIL_USERNAME,
      to: email,
      subject: 'Your password reset PIN',
      text: `Your PIN is: ${pin}. It will expire in 10 minutes.`,
    };

    await transporter.sendMail(mailOptions);

    res.json({ message: 'PIN sent to your email' });
  } catch (err) {
    console.error('❌ Reset error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

// ✅ ฟังก์ชั่น reset password
const confirmReset = async (req, res) => {
  const { email, pin, newPassword } = req.body;

  try {
    const user = await User.findOne({ email });
    if (!user) return res.status(404).json({ message: 'Email not found' });

    if (user.resetPin !== pin || new Date() > user.resetPinExpire) {
      return res.status(400).json({ message: 'Invalid or expired PIN' });
    }

    const hashed = await bcrypt.hash(newPassword, 10);
    user.password = hashed;
    user.resetPin = null;
    user.resetPinExpire = null;
    await user.save();

    res.json({ message: 'Password has been reset successfully' });
  } catch (err) {
    console.error('❌ Confirm reset error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};



// ✅ ฟังก์ชัน login
const login = async (req, res) => {
  const { username, password } = req.body;
  try {
    const user = await User.findOne({ username });
    if (!user) return res.status(400).json({ message: 'User not found' });

    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.status(401).json({ message: 'Invalid credentials' });


    if (!user.isEmailVerified) {
      return res.status(403).json({ message: 'Please verify your email first' });
    }

    const token = jwt.sign({
      id: user._id,
      role: user.role,
      username: user.username
    }, process.env.JWT_SECRET, { expiresIn: '7d' });
    
    res.json({
      token,
      user: {
        id: user._id,
        username: user.username,
        role: user.role,
        interests: user.interests,
      },
    });
    
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};

const changePassword = async (req, res) => {
  const { oldPassword, newPassword } = req.body;
  const user = await User.findById(req.user.id);

  if (!user) return res.status(404).json({ message: 'ไม่พบผู้ใช้' });

  const match = await bcrypt.compare(oldPassword, user.password);
  if (!match) return res.status(400).json({ message: 'รหัสผ่านเดิมไม่ถูกต้อง' });

  const hashed = await bcrypt.hash(newPassword, 10);
  user.password = hashed;
  await user.save();

  res.json({ message: 'เปลี่ยนรหัสผ่านเรียบร้อยแล้ว' });
};

const getMe = async (req, res) => {
  try {
    const user = await User.findById(req.user.id).select('-password');
    if (!user) return res.status(404).json({ message: 'ไม่พบผู้ใช้' });
    res.json(user);
  } catch (err) {
    console.error('❌ getMe error:', err.message);
    res.status(500).json({ message: 'เกิดข้อผิดพลาดในระบบ' });
  }
};



// ✅ export ทั้งสองฟังก์ชัน
module.exports = {
  register,
  login,
  requestReset,
  confirmReset,
  verifyEmail,
  resendVerification,
  changePassword,
  getMe
};
