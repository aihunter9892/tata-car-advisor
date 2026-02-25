"""
database.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All static data: Tata car specs + city profiles.
No logic here — just dictionaries.
Debug tip: print(TATA_CARS_DB.keys()) to list all cars.
"""

# ──────────────────────────────────────────
#  TATA MOTORS CAR DATABASE  (Feb 2026)
#  All prices in INR Lakhs (ex-showroom)
# ──────────────────────────────────────────
TATA_CARS_DB = {
    "Tata Punch": {
        "segment":          "Micro SUV",
        "price_min":         6.13,
        "price_max":         9.99,
        "fuel_types":        ["Petrol", "CNG", "EV"],
        "mileage_kmpl":      18.82,     # ARAI petrol
        "engine_cc":         1199,
        "power_ps":          86,
        "boot_litres":       366,
        "seats":             5,
        "ground_clearance":  190,       # mm
        "safety_rating":     5,         # GNCAP stars
        "ac_quality":        "Standard",
        "best_for":          ["City commute", "First car", "Budget buyers"],
        "not_good_for":      ["Long highway runs", "Hills at speed"],
        "emi_min":           8500,      # approx INR/month at min price
        "ev_range_km":       315,
        "usp":               "5-star safety in segment, rugged SUV stance",
    },
    "Tata Tiago": {
        "segment":          "Hatchback",
        "price_min":         5.60,
        "price_max":         8.49,
        "fuel_types":        ["Petrol", "CNG", "EV"],
        "mileage_kmpl":      19.80,
        "engine_cc":         1199,
        "power_ps":          86,
        "boot_litres":       242,
        "seats":             5,
        "ground_clearance":  165,
        "safety_rating":     4,
        "ac_quality":        "Standard",
        "best_for":          ["Tight budget", "City parking", "CNG savings"],
        "not_good_for":      ["Rough roads", "Large families"],
        "emi_min":           7800,
        "ev_range_km":       250,
        "usp":               "Most fuel-efficient Tata, lowest price of entry",
    },
    "Tata Tigor": {
        "segment":          "Compact Sedan",
        "price_min":         7.99,
        "price_max":        11.29,
        "fuel_types":        ["Petrol", "CNG", "EV"],
        "mileage_kmpl":      19.85,
        "engine_cc":         1199,
        "power_ps":          86,
        "boot_litres":       316,
        "seats":             5,
        "ground_clearance":  170,
        "safety_rating":     4,
        "ac_quality":        "Standard",
        "best_for":          ["Executive look", "CNG savings", "Sedan lovers"],
        "not_good_for":      ["Rough roads", "Hills"],
        "emi_min":          11100,
        "ev_range_km":       306,
        "usp":               "Only EV sedan in India under ₹12 lakhs",
    },
    "Tata Nexon": {
        "segment":          "Compact SUV",
        "price_min":         8.10,
        "price_max":        15.50,
        "fuel_types":        ["Petrol", "Diesel", "EV"],
        "mileage_kmpl":      17.01,     # diesel ARAI
        "engine_cc":         1497,
        "power_ps":          115,
        "boot_litres":       382,
        "seats":             5,
        "ground_clearance":  208,
        "safety_rating":     5,
        "ac_quality":        "Good",
        "best_for":          ["City + highway", "Young families", "EV early adopters"],
        "not_good_for":      ["Large families needing 7 seats"],
        "emi_min":          11200,
        "ev_range_km":       465,
        "usp":               "India's #1 selling EV, 5-star safety, highly versatile",
    },
    "Tata Altroz": {
        "segment":          "Premium Hatchback",
        "price_min":         6.60,
        "price_max":        10.89,
        "fuel_types":        ["Petrol", "Diesel", "CNG"],
        "mileage_kmpl":      19.38,
        "engine_cc":         1199,
        "power_ps":          100,
        "boot_litres":       345,
        "seats":             5,
        "ground_clearance":  165,
        "safety_rating":     5,
        "ac_quality":        "Excellent",
        "best_for":          ["Urban comfort", "Hot humid cities", "City professionals"],
        "not_good_for":      ["Bad roads", "Off-road use"],
        "emi_min":           9200,
        "ev_range_km":       None,
        "usp":               "Best AC in class, 5-star safety, premium cabin feel",
    },
    "Tata Harrier": {
        "segment":          "Midsize SUV",
        "price_min":        15.49,
        "price_max":        26.44,
        "fuel_types":        ["Diesel"],
        "mileage_kmpl":      16.35,
        "engine_cc":         1956,
        "power_ps":          170,
        "boot_litres":       425,
        "seats":             5,
        "ground_clearance":  205,
        "safety_rating":     5,
        "ac_quality":        "Excellent",
        "best_for":          ["Highway cruising", "Family trips", "Hilly terrain", "Status"],
        "not_good_for":      ["Tight city parking", "Petrol preference"],
        "emi_min":          21500,
        "ev_range_km":       None,
        "usp":               "ADAS safety features, most powerful Tata, commanding presence",
    },
    "Tata Safari": {
        "segment":          "Full-size SUV",
        "price_min":        16.19,
        "price_max":        27.34,
        "fuel_types":        ["Diesel"],
        "mileage_kmpl":      14.69,
        "engine_cc":         1956,
        "power_ps":          170,
        "boot_litres":       447,        # 5-seater config
        "seats":             7,
        "ground_clearance":  205,
        "safety_rating":     5,
        "ac_quality":        "Excellent",
        "best_for":          ["Large families", "7-seater need", "Long highway trips"],
        "not_good_for":      ["City parking", "Tight budgets"],
        "emi_min":          22500,
        "ev_range_km":       None,
        "usp":               "Only 7-seater in Tata lineup, massive presence, highway master",
    },
    "Tata Curvv": {
        "segment":          "Coupe SUV",
        "price_min":        10.00,
        "price_max":        19.00,
        "fuel_types":        ["Petrol", "Diesel", "EV"],
        "mileage_kmpl":      18.01,
        "engine_cc":         1497,
        "power_ps":          125,
        "boot_litres":       500,
        "seats":             5,
        "ground_clearance":  200,
        "safety_rating":     5,
        "ac_quality":        "Excellent",
        "best_for":          ["Style seekers", "Tech lovers", "EV transition"],
        "not_good_for":      ["Rear legroom sensitive buyers", "Very tight budgets"],
        "emi_min":          13900,
        "ev_range_km":       502,
        "usp":               "Largest boot in segment, best EV range, futuristic design",
    },
    "Tata Sierra EV": {
        "segment":          "Electric SUV",
        "price_min":        25.00,
        "price_max":        30.00,
        "fuel_types":        ["EV"],
        "mileage_kmpl":      None,       # EV — no kmpl
        "engine_cc":         None,
        "power_ps":          200,
        "boot_litres":       510,
        "seats":             5,
        "ground_clearance":  210,
        "safety_rating":     5,
        "ac_quality":        "Excellent",
        "best_for":          ["EV enthusiasts", "Premium segment", "Green buyers"],
        "not_good_for":      ["Long trips without chargers", "Budget buyers"],
        "emi_min":          34700,
        "ev_range_km":       420,
        "usp":               "Iconic nameplate reborn as EV, most powerful Tata passenger car",
    },
}


# ──────────────────────────────────────────
#  CITY CLIMATE PROFILES
#  Used as fallback when weather API fails
# ──────────────────────────────────────────
CITY_PROFILES = {
    "Mumbai":    {"humidity": "very_high", "terrain": "flat",        "type": "coastal"},
    "Chennai":   {"humidity": "very_high", "terrain": "flat",        "type": "coastal"},
    "Kochi":     {"humidity": "very_high", "terrain": "flat",        "type": "coastal"},
    "Kolkata":   {"humidity": "high",      "terrain": "flat",        "type": "plains"},
    "Bangalore": {"humidity": "moderate",  "terrain": "flat",        "type": "highland"},
    "Pune":      {"humidity": "moderate",  "terrain": "hilly",       "type": "highland"},
    "Delhi":     {"humidity": "low",       "terrain": "flat",        "type": "plains"},
    "Lucknow":   {"humidity": "moderate",  "terrain": "flat",        "type": "plains"},
    "Hyderabad": {"humidity": "low",       "terrain": "flat",        "type": "semi-arid"},
    "Ahmedabad": {"humidity": "low",       "terrain": "flat",        "type": "semi-arid"},
    "Jaipur":    {"humidity": "very_low",  "terrain": "flat",        "type": "desert"},
    "Shimla":    {"humidity": "low",       "terrain": "steep_hills", "type": "mountain"},
}


# ──────────────────────────────────────────
#  REFERENCE FUEL PRICES  (Feb 2026, INR/L)
#  Used when live API is unavailable
# ──────────────────────────────────────────
REFERENCE_FUEL_PRICES = {
    "Petrol": {
        "Mumbai": 104.21, "Delhi": 94.72, "Chennai": 100.29,
        "Bangalore": 102.86, "Kolkata": 105.41, "Hyderabad": 107.41,
        "Pune": 104.29, "Ahmedabad": 96.63, "Kochi": 107.71,
        "Jaipur": 99.72, "Lucknow": 94.76, "Shimla": 103.42,
        "DEFAULT": 100.00,
    },
    "Diesel": {
        "Mumbai": 92.15, "Delhi": 87.62, "Chennai": 92.44,
        "Bangalore": 88.94, "Kolkata": 92.76, "Hyderabad": 95.65,
        "Pune": 91.42, "Ahmedabad": 89.33, "Kochi": 96.26,
        "Jaipur": 90.21, "Lucknow": 87.61, "Shimla": 91.10,
        "DEFAULT": 91.00,
    },
    "CNG": {
        "Mumbai": 73.00, "Delhi": 74.09, "Pune": 75.50,
        "Ahmedabad": 68.15,
        "DEFAULT": 74.00,
    },
}
