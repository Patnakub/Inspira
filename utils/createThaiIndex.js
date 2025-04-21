// ติดตั้งด้วย: npm install @elastic/elasticsearch
const { Client } = require('@elastic/elasticsearch');

const client = new Client({
  node: 'http://localhost:9200', // เปลี่ยน URL ตามที่ใช้งาน
});

async function createIndex() {
  const indexName = 'exhibitions';

  // ถ้ามี Index เดิมอยู่แล้ว ให้ลบทิ้งก่อน
  const indexExists = await client.indices.exists({ index: indexName });
  if (indexExists) {
    console.log(`ℹ️ ลบ Index เดิม: ${indexName}`);
    await client.indices.delete({ index: indexName });
  }

  // สร้าง Index ใหม่พร้อม Thai Analyzer
  await client.indices.create({
    index: indexName,
    body: {
      settings: {
        analysis: {
          analyzer: {
            thai_analyzer: {
              type: 'custom',
              tokenizer: 'icu_tokenizer'
            }
          }
        }
      },
      mappings: {
        properties: {
          title: {
            type: 'text',
            analyzer: 'thai_analyzer'
          },
          description: {
            type: 'text',
            analyzer: 'thai_analyzer'
          },
          categories: {
            type: 'keyword'
          },
          start_date: {
            type: 'date'
          },
          end_date: {
            type: 'date'
          },
          location: {
            type: 'keyword'
          },
          status: {
            type: 'keyword'
          }
        }
      }
    }
  });

  console.log(`✅ สร้าง Index '${indexName}' พร้อม Thai Analyzer สำเร็จ`);
}

createIndex().catch(console.error);
