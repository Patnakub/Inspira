const { Client } = require('@elastic/elasticsearch');

const client = new Client({ node: 'http://localhost:9200' });

async function createIndex() {
  const indexName = 'exhibitions_th';

  // ลบ index เดิมถ้ามี
  const exists = await client.indices.exists({ index: indexName });
  if (exists) {
    await client.indices.delete({ index: indexName });
    console.log('🗑️ ลบ index เดิมแล้ว');
  }

  // สร้างใหม่
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
          categories: { type: 'keyword' },
          location: { type: 'keyword' },
          status: { type: 'keyword' },
          start_date: { type: 'date' },
          end_date: { type: 'date' }
        }
      }
    }
  });

  console.log('✅ สร้าง index exhibitions_th พร้อม analyzer สำเร็จ');
}

createIndex().catch(console.error);
