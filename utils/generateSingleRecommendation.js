const { MongoClient } = require("mongodb");
const cosineSimilarity = require("compute-cosine-similarity");
require("dotenv").config();

module.exports = async function generateForNewUser(user) {
  const client = new MongoClient(process.env.MONGODB_URI);

  try {
    await client.connect();
    const db = client.db("exhibition_db");
    const exhibitionsCol = db.collection("exhibitions");
    const recommendationsCol = db.collection("recommendations");

    const exhibitions = await exhibitionsCol.find({ status: { $in: ["ongoing", "upcoming"] } }).toArray();
    if (exhibitions.length === 0) return;

    const categories = await db.collection("categories").find().toArray();
    const categoryNames = categories
      .map(c => typeof c.name === 'string' ? c.name.trim() : null)
      .filter(Boolean);

    const interests = Array.isArray(user.interests)
      ? user.interests
          .filter(i => typeof i === 'string')
          .map(i => i.trim())
          .filter(i => categoryNames.includes(i))
      : [];

    const userVec = categoryNames.map(cat => interests.includes(cat) ? 1 : 0);

    const results = exhibitions.map(ex => {
      const exCats = Array.isArray(ex.categories)
        ? ex.categories.filter(c => typeof c === 'string')
        : [];

      const exVec = categoryNames.map(cat => exCats.includes(cat) ? 1 : 0);

      const score = cosineSimilarity(userVec, exVec);
      return {
        event_id: ex._id.toString(),
        score: parseFloat(score.toFixed(4))
      };
    });

    results.sort((a, b) => b.score - a.score);

    await recommendationsCol.insertOne({
      user_id: user._id?.toString() || '',
      recommendations: results,
      updated_at: new Date()
    });

    console.log("✅ Recommendation สำหรับผู้ใช้ใหม่ถูกสร้างแล้ว");
  } catch (err) {
    console.error("❌ Error in generateForNewUser:", err.message);
  } finally {
    await client.close();
  }
};
