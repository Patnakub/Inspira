// เชื่อมต่อ elasticsearch
const { Client } = require('@elastic/elasticsearch');

const elasticClient = new Client({
  node: 'http://127.0.0.1:9200', // ✅ ใช้ IPv4 แทน localhost (หลีกเลี่ยง ::1)
  sniffOnStart: false,          // ✅ ปิด sniffing
  sniffInterval: false,
  compression: false            // ✅ ปิดการบีบอัด ถ้าใช้ bulk จะเสถียรกว่า
});

module.exports = elasticClient;
