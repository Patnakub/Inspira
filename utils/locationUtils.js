// utils/locationUtils.js
const axios = require("axios");
const GOOGLE_API_KEY = process.env.GOOGLE_API_KEY;

function normalizeLocation(location) {
  if (!location || typeof location !== "string") return location;
  location = location.trim();

  const knownReplacements = {
    "impact": "อิมแพ็ค เมืองทองธานี",
    "paragon hall": "Paragon Hall",
    "QSNCC": "ศูนย์การประชุมแห่งชาติสิริกิติ์",
    "BITEC": "ไบเทค บางนา",
    "EH106": "ไบเทค บางนา",
    "ไบเทคฮอลล์": "ไบเทค บางนา",
    "BHIRAJ HALL": "ไบเทค บางนา",
    "TCDC": "TCDC",
    "BACC": "BACC",
    "River City Bangkok": "River City Bangkok",
    "Samyan Mitrtown": "Samyan Mitrtown",
    "Seacon Square": "Seacon Square",
    "Fashion Island": "Fashion Island",
    "Paragon Hall": "Paragon Hall",
    "TRUE ICON HALL": "TRUE ICON HALL",
    "Atta Gallery": "Atta Gallery",
    "MAD Art Destination": "MAD Art Destination",
    "Xspace Bangkok": "Xspace Bangkok",
    "Explode Gallery Bangkok": "Explode Gallery Bangkok",
    "Agni Gallery Bangkok": "Agni Gallery Bangkok",
    "La Lanta Fine Art Bangkok": "La Lanta Fine Art Bangkok",
    "HOP Photo Gallery Bangkok": "HOP Photo Gallery Bangkok"
  };

  for (const [key, val] of Object.entries(knownReplacements)) {
    if (location.toLowerCase().includes(key.toLowerCase())) return val;
  }

  location = location.replace(/Hall\s?\d+|EH\d+|Plenary Hall|\bZone\s?[A-Za-z]+\b|อาคาร\s?[A-Za-z0-9]+|The Portal Lifestyle Complex|\s{2,}/gi, "").trim();
  return location;
}

async function getFromGoogle(location) {
  try {
    const url = `https://maps.googleapis.com/maps/api/geocode/json`;
    const { data } = await axios.get(url, {
      params: { address: location, key: GOOGLE_API_KEY },
    });
    if (data.status === "OK") {
      const result = data.results[0].geometry.location;
      return { lat: result.lat, lon: result.lng };
    }
  } catch (e) {
    console.error("[Google]", e.message);
  }
  return null;
}

async function getFromPlaces(location) {
  try {
    const url = `https://maps.googleapis.com/maps/api/place/textsearch/json`;
    const { data } = await axios.get(url, {
      params: { query: location, key: GOOGLE_API_KEY },
    });
    if (data.status === "OK" && data.results.length > 0) {
      const place = data.results[0].geometry.location;
      return { lat: place.lat, lon: place.lng };
    }
  } catch (e) {
    console.error("[Places]", e.message);
  }
  return null;
}

async function getFromNominatim(location) {
  try {
    const url = `https://nominatim.openstreetmap.org/search`;
    const { data } = await axios.get(url, {
      params: { q: location, format: "json", limit: 1 },
      headers: { "User-Agent": "ExhibitionProject/1.0 (example@email.com)" }
    });
    if (data && data.length > 0) {
      return { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) };
    }
  } catch (e) {
    console.error("[Nominatim]", e.message);
  }
  return null;
}

async function getLatLonWithFallback(location) {
  const normalized = normalizeLocation(location);
  console.log("🌐 แปลงพิกัดจาก (normalized):", normalized);
  
  let result = await getFromGoogle(normalized);
  if (result) return result;

  result = await getFromPlaces(normalized);
  if (result) return result;

  result = await getFromNominatim(normalized);
  if (result) return result;

  return null;
}

module.exports = { getLatLonWithFallback };