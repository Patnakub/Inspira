// middlewares/checkAdmin.js
function checkAdmin(req, res, next) {
    if (!req.user || req.user.role !== "admin") {
      return res.status(403).json({ message: "ต้องเป็นแอดมินเท่านั้น" });
    }
    next();
  }
  
  module.exports = checkAdmin;
  