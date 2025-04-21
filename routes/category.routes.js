// routes/category.routes.js
const express = require('express')
const router = express.Router()
const Category = require('../models/Category')

router.get('/', async (req, res) => {
  try {
    const categories = await Category.find().sort('name')
    res.json(categories)
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

module.exports = router
