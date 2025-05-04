const express = require('express');
const router = express.Router();
const auth = require('../middlewares/auth');
const { getUserRecommendations } = require('../controllers/recommendation.controller');

router.get('/:userId', auth, getUserRecommendations);

module.exports = router;
