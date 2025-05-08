const elasticClient = require('./elasticClient');

const syncExhibitionToElastic = async (exhibition) => {
  if (!elasticClient) {
    console.warn("⚠️ Elasticsearch client not available — skipping sync for:", exhibition.title);
    return;
  }

  try {
    await elasticClient.index({
      index: 'exhibitions_th',
      id: exhibition._id.toString(),
      document: {
        title: exhibition.title,
        description: exhibition.description,
      },
    });
  } catch (err) {
    console.error(`❌ Failed to sync exhibition "${exhibition.title}"`, err);
  }
};

module.exports = { syncExhibitionToElastic };
