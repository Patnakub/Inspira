const express = require('express');
const router = express.Router();
const { getUserRecommendations } = require('../controllers/recommendation.controller');

router.get('/:userId', getUserRecommendations);

module.exports = router;
