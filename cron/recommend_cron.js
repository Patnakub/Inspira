const cron = require("node-cron");
const { exec } = require("child_process");
const path = require("path");

const scriptPath = path.join(__dirname, "../utils/generateRecommendations.py");  // ✅ อัปเดต path ใหม่

// ทุก 14 วัน เวลา 00:00 น.
cron.schedule("0 0 */14 * *", () => {
    console.log("เริ่มรันระบบแนะนำ");
    exec(`python "${scriptPath}"`, (error, stdout, stderr) => {
      if (error) {
        console.error(`error: ${error.message}`);
        return;
      }
      if (stderr) {
        console.warn(`stderr: ${stderr}`);
      }
      console.log(`stdout:\n${stdout}`);
    });
  });
  