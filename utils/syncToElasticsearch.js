const Exhibition = require('../models/Exhibition');
const { syncExhibitionToElastic } = require('./elasticSync');

const syncExhibitionsToElasticsearch = async () => {
  try {
    const exhibitions = await Exhibition.find({}, '_id title description');

    for (const ex of exhibitions) {
      await syncExhibitionToElastic(ex); // ฟังก์ชันนี้จะเช็ค elasticClient ให้อยู่แล้ว
    }

    console.log(`✅ Synced ${exhibitions.length} exhibitions to Elasticsearch`);
  } catch (err) {
    console.error('❌ Sync failed:', err);
  }
};

module.exports = syncExhibitionsToElasticsearch;
