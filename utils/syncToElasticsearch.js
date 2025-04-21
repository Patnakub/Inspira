const Exhibition = require('../models/Exhibition');
const { syncExhibitionToElastic } = require('./elasticSync');

const syncExhibitionsToElasticsearch = async () => {
  try {
    const exhibitions = await Exhibition.find({}, '_id title description');
    for (const ex of exhibitions) {
      await syncExhibitionToElastic(ex);
    }
    console.log(`✅ Synced ${exhibitions.length} exhibitions to Elasticsearch`);
  } catch (err) {
    console.error('❌ Sync failed:', err);
  }
};

module.exports = syncExhibitionsToElasticsearch;
