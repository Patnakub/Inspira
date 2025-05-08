const { Client } = require('@elastic/elasticsearch');

let elasticClient = null;

if (process.env.ELASTIC_NODE) {
  elasticClient = new Client({
    node: process.env.ELASTIC_NODE,
    sniffOnStart: false,
    sniffInterval: false,
    compression: false
  });
} else {
  console.warn("⚠️ ELASTIC_NODE not defined — Elasticsearch client disabled.");
}

module.exports = elasticClient;
