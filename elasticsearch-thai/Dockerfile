# ใช้ Elasticsearch เวอร์ชันที่ต้องการ
FROM docker.elastic.co/elasticsearch/elasticsearch:8.5.0

# ติดตั้ง plugin ที่จำเป็นสำหรับ Thai Analyzer
RUN elasticsearch-plugin install analysis-icu --batch
