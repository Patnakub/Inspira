// utils/generateSingleRecommendation.js
const { MongoClient, ObjectId } = require("mongodb");
const cosineSimilarity = require("compute-cosine-similarity");
require("dotenv").config();

module.exports = async function generateForNewUser(user) {
  const client = new MongoClient(process.env.MONGO_URI);
  await client.connect();

  const db = client.db("exhibition_db");
  const exhibitionsCol = db.collection("exhibitions");
  const recommendationsCol = db.collection("recommendations");

  const exhibitions = await exhibitionsCol.find({ status: { $in: ["ongoing", "upcoming"] } }).toArray();
  if (exhibitions.length === 0) return;

  const categories = await db.collection("categories").find().toArray();
  const categoryNames = categories.map(c => c.name);

  const userVec = categoryNames.map(cat => user.interests?.includes(cat) ? 1 : 0);

  const results = exhibitions.map(ex => {
    const exVec = categoryNames.map(cat => ex[cat] || 0);
    const score = cosineSimilarity(userVec, exVec);
    return { event_id: ex._id.toString(), score: parseFloat(score.toFixed(4)) };
  });

  results.sort((a, b) => b.score - a.score);

  await recommendationsCol.insertOne({
    user_id: user._id.toString(),
    recommendations: results,
    updated_at: new Date()
  });

  await client.close();
  console.log("✅ Recommendation สำหรับผู้ใช้ใหม่ถูกสร้างแล้ว");
};
