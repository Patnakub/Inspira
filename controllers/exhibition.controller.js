const Exhibition = require('../models/Exhibition');
const elasticClient = require('../utils/elasticClient');

exports.getAllExhibitions = async (req, res) => {
  try {
    const skip = parseInt(req.query.skip) || 0;
    const limit = parseInt(req.query.limit) || 10;

    const exhibitions = await Exhibition.find()
      .sort({ start_date_obj: 1 })
      .skip(skip)
      .limit(limit);

    const totalCount = await Exhibition.countDocuments();

    res.json({
      total: totalCount,
      data: exhibitions,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};


exports.searchExhibitions = async (req, res) => {
  const { q } = req.query;
  if (!q) return res.status(400).json({ message: 'Missing query parameter: q' });

  try {
    const esResult = await elasticClient.search({
      index: 'exhibitions_th',
      query: {
        bool: {
          should: [
            {
              multi_match: {
                query: q,
                fields: ['title^2', 'description'],
                fuzziness: 'AUTO'
              }
            },
            {
              match: {
                title: {
                  query: q,
                  analyzer: 'thai_analyzer'
                }
              }
            },
            {
              match: {
                description: {
                  query: q,
                  analyzer: 'thai_analyzer'
                }
              }
            }
          ]
        }
      },
      size: 20
    });

    const ids = esResult.hits.hits.map(hit => hit._id);
    const exhibitions = await Exhibition.find({ _id: { $in: ids } });

    const exhibitionMap = new Map();
    exhibitions.forEach(ex => exhibitionMap.set(ex._id.toString(), ex));

    const orderedResults = ids.map(id => exhibitionMap.get(id)).filter(Boolean);

    res.json(orderedResults);
  } catch (err) {
    console.error('Search error:', err);
    res.status(500).json({ message: 'Search failed' });
  }
};


exports.getOngoingExhibitions = async (req, res) => {
  try {
    const ongoing = await Exhibition.find({ status: 'ongoing' })
      .sort({ end_date_obj: 1 })  // ✅ เรียงจากใกล้จบ → ไกล
      .select('title location cover_picture');

    res.json(ongoing);
  } catch (err) {
    res.status(500).json({ message: 'Failed to fetch ongoing exhibitions' });
  }
};

  
exports.getUpcomingExhibitions = async (req, res) => {
    try {
      const upcoming = await Exhibition.find({ status: 'upcoming' })
      .sort({ start_date_obj: 1 })  // ใกล้วันจัดก่อน
      .select('title location cover_picture');

      res.json(upcoming);
    } catch (err) {
      res.status(500).json({ message: 'Failed to fetch upcoming exhibitions' });
    }
  };

// ดึงข้อมูลโดยกรองตาม status และ category
exports.getFilteredExhibitions = async (req, res) => {
  try {
    const { status, category, page = 1, limit = 10 } = req.query;

    const query = {};
    if (status) query.status = status;
    if (category) query.categories = { $in: [category] };

    const skip = (parseInt(page) - 1) * parseInt(limit);

    // ✅ เลือก field ที่เหมาะสมสำหรับแต่ละสถานะ
    let sortOption = {};
    if (status === 'ongoing') {
      sortOption = { end_date_obj: 1 };         // ใกล้จบก่อน
    } else if (status === 'past') {
      sortOption = { end_date_obj: -1 };        // จบล่าสุดก่อน
    } else {
      sortOption = { start_date_obj: 1 };       // ใกล้เริ่มก่อน
    }

    const exhibitions = await Exhibition.find(query)
      .sort(sortOption)
      .skip(skip)
      .limit(parseInt(limit));

    res.json(exhibitions);
  } catch (err) {
    console.error('❌ Filter error:', err);
    res.status(500).json({ message: 'Server error' });
  }
};


exports.getExhibitionById = async (req, res) => {
    try {
      const exhibition = await Exhibition.findById(req.params.id);
      if (!exhibition) {
        return res.status(404).json({ message: 'Exhibition not found' });
      }
      res.json(exhibition);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  };
  
const BusStop = require('../models/BusStop'); // import model ป้ายรถเมล์

const haversineDistance = (lat1, lon1, lat2, lon2) => {
  const toRad = deg => (deg * Math.PI) / 180;
  const R = 6371000; // meters
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

exports.getNearbyBusStops = async (req, res) => {
  try {
    const exhibition = await Exhibition.findById(req.params.id);
    if (!exhibition) return res.status(404).json({ message: 'Exhibition not found' });

    const exLat = parseFloat(exhibition.latitude);
    const exLon = parseFloat(exhibition.longitude);
    if (isNaN(exLat) || isNaN(exLon)) return res.status(400).json({ message: 'Missing coordinates' });

    const busStops = await BusStop.find({});
    const nearby = [];

    for (const stop of busStops) {
      const dist = haversineDistance(
        exLat, exLon,
        Number(stop.latitude), Number(stop.longitude)
      );
      if (dist <= 1000) { // ขยาย radius ให้พอมีผลลัพธ์
        nearby.push({
          stop_name: stop.stop_name,
          routes: stop.routes.map(route => ({
            short_name: route.short_name,  // แสดงหมายเลขสาย
            long_name: route.long_name     // แสดงชื่อสาย
          })),
          min_price: stop.min_price,
          max_price: stop.max_price,
          distance: Math.round(dist) // เมตร
        });
      }
    }

    // จัดอันดับระยะทางและเลือก 10 อันดับแรก
    nearby.sort((a, b) => a.distance - b.distance);
    res.json(nearby.slice(0, 10));
  } catch (err) {
    res.status(500).json({ message: 'Server error' });
  }
};

