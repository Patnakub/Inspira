const getDistance = require("../utils/haversine");
const fs = require("fs");
const path = require("path");

const stopsPath = path.join(__dirname, "../gtfs/stops.txt");
const stopTimesPath = path.join(__dirname, "../gtfs/stop_times.txt");
const tripsPath = path.join(__dirname, "../gtfs/trips.txt");
const routesPath = path.join(__dirname, "../gtfs/routes.txt");

function loadGTFS(filePath) {
  const data = fs.readFileSync(filePath, "utf8");
  const [header, ...rows] = data.trim().split("\n");
  const keys = header.split(",").map(k => k.trim().replace(/^"|"$/g, ""));
  return rows.map((line) => {
    const values = line.split(",").map(v => v.trim().replace(/^"|"$/g, ""));
    return Object.fromEntries(keys.map((k, i) => [k, values[i]]));
  });
}

const stops = loadGTFS(stopsPath);
const stopTimes = loadGTFS(stopTimesPath);
const trips = loadGTFS(tripsPath);
const routes = loadGTFS(routesPath);

function getRoutesByStopId(stop_id) {
  const normStopId = stop_id.toString().trim();

  const tripIds = stopTimes
    .filter(st => st.stop_id === normStopId)
    .map(st => st.trip_id);

  const routeIds = trips
    .filter(t => tripIds.includes(t.trip_id))
    .map(t => {
      return t.route_id?.toString().trim();
    });

  return [...new Set(routeIds)];
}


function findClosestStop(lat, lng) {
  const point = { lat: parseFloat(lat), lng: parseFloat(lng) };
  return stops.map(stop => ({
    ...stop,
    distance: getDistance(
      parseFloat(lat),
      parseFloat(lng),
      parseFloat(stop.stop_lat),
      parseFloat(stop.stop_lon)
    )
    
  })).sort((a, b) => a.distance - b.distance)[0];
}

function findNearbyStops(lat, lng, limit = 10) {
  const point = { lat: parseFloat(lat), lng: parseFloat(lng) };
  return stops.map(stop => ({
    ...stop,
    distance: getDistance(
      parseFloat(lat),
      parseFloat(lng),
      parseFloat(stop.stop_lat),
      parseFloat(stop.stop_lon)
    )
    
  })).sort((a, b) => a.distance - b.distance).slice(0, limit);
}

function canTravelBetweenStopsOnSameRoute(routeId, startStopId, endStopId) {
  const routeTrips = trips.filter(t => t.route_id === routeId);

  const tripsWithStart = new Set(
    stopTimes
      .filter(st => st.stop_id === startStopId && routeTrips.some(t => t.trip_id === st.trip_id))
      .map(st => st.trip_id)
  );

  const tripsWithEnd = new Set(
    stopTimes
      .filter(st => st.stop_id === endStopId && routeTrips.some(t => t.trip_id === st.trip_id))
      .map(st => st.trip_id)
  );

  return tripsWithStart.size > 0 && tripsWithEnd.size > 0;
}

exports.suggestRoute = (req, res) => {
  try {
    const { lat, lng, exLat, exLng } = req.query;
    const { userStops } = req.body || {};

    if (!exLat || !exLng || (!userStops && (!lat || !lng))) {
      return res.status(400).json({ error: "Missing required data" });
    }

    if (userStops) {
      return suggestCore(userStops, { lat: exLat, lng: exLng }, res);
    } else {
      return suggestCore({ lat, lng }, { lat: exLat, lng: exLng }, res);
    }
  } catch (err) {
    console.error("❌ Internal error in suggestRoute:", err);
    return res.status(500).json({ error: "Internal server error" });
  }
};


exports.getAllStops = (req, res) => {
  const stopsData = stops.map(stop => ({
    stop_name: stop.stop_name.replace(/"/g, ''),
    stop_id: stop.stop_id,
    lat: stop.stop_lat,
    lon: stop.stop_lon,
  }));
  res.json(stopsData);
};

exports.suggestRouteFromStops = (req, res) => {
  const { userStops } = req.body;
  const { exLat, exLng } = req.query;
  if (!Array.isArray(userStops) || !exLat || !exLng) {
    return res.status(400).json({ error: "Missing stop data or coordinates" });
  }
  return exports.suggestRoute(req, res);
};

function suggestCore(userInput, exhibition, res) {
  const exhibitionNearby = findNearbyStops(exhibition.lat, exhibition.lng, 100)
    .filter(stop => getRoutesByStopId(stop.stop_id).length > 0);

  let userNearby = [];

  if (Array.isArray(userInput)) {
    userNearby = stops.filter(stop => userInput.includes(stop.stop_id));
  } else {
    userNearby = findNearbyStops(userInput.lat, userInput.lng, 100);
  }

  const allMatches = [];
  const seenRoutes = new Set();

  for (let uStop of userNearby) {
    uStop.distance = uStop.distance || getDistance(userInput.lat, userInput.lng, uStop.stop_lat, uStop.stop_lon);
    const uRoutes = getRoutesByStopId(uStop.stop_id);

    for (let eStop of exhibitionNearby) {
      eStop.distance = eStop.distance || getDistance(exhibition.lat, exhibition.lng, eStop.stop_lat, eStop.stop_lon);
      const eRoutes = getRoutesByStopId(eStop.stop_id);

      const commonRoutes = uRoutes.filter(r => eRoutes.includes(r));

      for (let r of commonRoutes) {
        const matchKey = `${r}-${uStop.stop_id}-${eStop.stop_id}`;
        if (!seenRoutes.has(matchKey)) {
          seenRoutes.add(matchKey);

          const routeInfo = routes.find(route => route.route_id?.trim() === r.toString().trim());
          const routeShort = routeInfo?.route_short_name?.trim() || r;
          const routeLong = routeInfo?.route_long_name?.trim() || '';

          allMatches.push({
            get_on: uStop.stop_name,
            get_off: eStop.stop_name,
            get_on_distance: parseFloat(uStop.distance.toFixed(0)),
            get_off_distance: parseFloat(eStop.distance.toFixed(0)),
            distance: (uStop.distance + eStop.distance).toFixed(0),
            route: {
              id: r,
              short_name: routeShort,
              long_name: routeLong
            }
          });
        }
      }
    }
  }

  if (allMatches.length > 0) {
    allMatches.sort((a, b) => a.distance - b.distance);
    // 🔽 กรองให้เหลือสายละ 1 เส้นทาง โดยเลือกปลายทางที่ใกล้ที่สุด
    const closestByRoute = new Map();

    for (const match of allMatches) {
      const routeId = match.route.id;
      const existing = closestByRoute.get(routeId);

      if (!existing || parseFloat(match.get_off_distance) < parseFloat(existing.get_off_distance)) {
        closestByRoute.set(routeId, match);
      }
    }

    const filteredMatches = Array.from(closestByRoute.values());
    filteredMatches.sort((a, b) => parseFloat(a.distance) - parseFloat(b.distance));

    return res.json(filteredMatches.slice(0, 10));

  } else {
    return res.json({ message: "ไม่พบเส้นทางที่นั่งสายเดียวได้" });
  }
}
