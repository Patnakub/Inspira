const elasticClient = require('./elasticClient');

const syncExhibitionToElastic = async (exhibition) => {
  await elasticClient.index({
    index: 'exhibitions_th',
    id: exhibition._id.toString(),
    document: {
      title: exhibition.title,
      description: exhibition.description,
    },
  });
};

module.exports = { syncExhibitionToElastic };
