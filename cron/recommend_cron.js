// recommend_cron.js - สำหรับ GitHub Actions
const { exec } = require("child_process");
const path = require("path");

const scriptPath = path.join(__dirname, "../utils/generateRecommendations.py");

console.log("🔁 เริ่มรันระบบแนะนำ...");
exec(`python "${scriptPath}"`, (error, stdout, stderr) => {
  if (error) {
    console.error(`❌ error: ${error.message}`);
    process.exit(1);
  }
  if (stderr) {
    console.warn(`⚠️ stderr: ${stderr}`);
  }
  console.log(`✅ stdout:\n${stdout}`);
});
