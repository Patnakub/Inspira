const { Client } = require('@elastic/elasticsearch');

const elasticClient = new Client({
  node: process.env.ELASTIC_NODE,
  sniffOnStart: false,
  sniffInterval: false,
  compression: false
});

module.exports = elasticClient;
