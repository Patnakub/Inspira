const express = require("express");
const router = express.Router();
const routeController = require("../controllers/route.controller");

// สำหรับพิกัด → GET
router.get("/suggest-route", routeController.suggestRoute);

// สำหรับ stop_id หลายป้าย → POST
router.post("/suggest-route", routeController.suggestRouteFromStops);

router.get("/all-stops", routeController.getAllStops);

module.exports = router;
