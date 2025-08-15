const express = require("express");
const router = express.Router();
const routeController = require("../controllers/route.controller");

// สำหรับพิกัด → GET
router.get("/suggest-route", routeController.suggestRoute);

router.get("/all-stops", routeController.getAllStops);

router.post("/suggest-route-from-stops", routeController.suggestRouteFromStops);

module.exports = router;
