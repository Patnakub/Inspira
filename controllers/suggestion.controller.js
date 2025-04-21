const Suggestion = require("../models/Suggestion");
const { getLatLonWithFallback } = require("../utils/locationUtils");

exports.createSuggestion = async (req, res) => {
  try {
    const {
      title,
      location,
      start_date,
      end_date,
      event_slot_time,
      categories = [],
      description,
      latitude,
      longitude,
      ticket = "ไม่ระบุ",
      ticket_price = ""
    } = req.body;

    let lat = parseFloat(latitude);
    let lon = parseFloat(longitude);

    if (!lat || !lon || isNaN(lat) || isNaN(lon)) {
      const coords = await getLatLonWithFallback(location);
      lat = coords?.lat ?? null;
      lon = coords?.lon ?? null;
    }
    console.log("📩 req.body.ticket:", req.body.ticket);
    console.log("📩 req.body.ticket_price:", req.body.ticket_price);

    const ticketPriceArray = ticket === "มีค่าเข้าชม"
      ? ticket_price.split(",").map(p => parseInt(p.trim())).filter(p => !isNaN(p))
      : [];

    const suggestion = new Suggestion({
      title,
      location,
      start_date,
      end_date,
      event_slot_time,
      categories,
      description,
      image_url: `/uploads/suggestions/${req.file.filename}`,
      latitude: lat,
      longitude: lon,
      ticket,
      ticket_price: ticketPriceArray,
    });

    await suggestion.save();
    res.json({ success: true, suggestion });
  } catch (err) {
    console.error("❌ Error creating suggestion:", err);
    res.status(500).json({ success: false, error: "Server error" });
  }
};
