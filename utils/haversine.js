// 📁 utils/haversine.js
const haversine = require('haversine-distance');

function getDistance(lat1, lon1, lat2, lon2) {
  return haversine({ lat: lat1, lon: lon1 }, { lat: lat2, lon: lon2 });
}

module.exports = getDistance;
