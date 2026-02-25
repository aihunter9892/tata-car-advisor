"""
tools.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The 4 tools the agent can call:
  1. get_city_weather()   → wttr.in (live) or city profile (fallback)
  2. get_tata_cars()      → filter TATA_CARS_DB
  3. get_fuel_price()     → reference prices (Feb 2026)
  4. calculate_tco()      → pure Python finance math

Debug any tool independently:
    python tools.py
"""

import json
import requests
from database import TATA_CARS_DB, CITY_PROFILES, REFERENCE_FUEL_PRICES


# ══════════════════════════════════════════
#  TOOL 1 — City Weather
# ══════════════════════════════════════════
def get_city_weather(city: str) -> dict:
    """
    Get current temperature, humidity, and terrain info for an Indian city.
    Tries wttr.in live API first; falls back to CITY_PROFILES on failure.

    Args:
        city: Indian city name e.g. 'Mumbai', 'Delhi', 'Shimla'

    Returns:
        dict with temperature_c, humidity_pct, terrain, ac_importance, source
    """
    print(f"  [TOOL] get_city_weather(city='{city}')")

    try:
        url  = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})

        if resp.status_code == 200:
            data    = resp.json()
            current = data["current_condition"][0]
            temp_c  = int(current["temp_C"])
            hum     = int(current["humidity"])
            desc    = current["weatherDesc"][0]["value"]
            profile = CITY_PROFILES.get(city, {})

            result = {
                "city":          city,
                "temperature_c": temp_c,
                "humidity_pct":  hum,
                "description":   desc,
                "terrain":       profile.get("terrain", "flat"),
                "ac_importance": (
                    "HIGH"     if (hum > 70 or temp_c > 35) else
                    "MODERATE" if temp_c > 28 else "LOW"
                ),
                "source": "wttr.in (live)",
            }
            print(f"    → {temp_c}°C, {hum}% humidity, AC: {result['ac_importance']}")
            return result

    except Exception as e:
        print(f"    → wttr.in failed ({e}), using city profile fallback")

    # ── Fallback: city profile ──
    profile = CITY_PROFILES.get(city, {"humidity": "moderate", "terrain": "flat"})
    hum_map = {"very_high": 85, "high": 70, "moderate": 55, "low": 35, "very_low": 20}
    hum_val = hum_map.get(profile["humidity"], 55)

    result = {
        "city":          city,
        "temperature_c": 32 if profile["humidity"] in ("very_high", "high") else 25,
        "humidity_pct":  hum_val,
        "description":   "Estimated from city climate profile",
        "terrain":       profile.get("terrain", "flat"),
        "ac_importance": (
            "HIGH"     if profile["humidity"] in ("very_high", "high") else
            "MODERATE" if profile["humidity"] == "moderate" else "LOW"
        ),
        "source": "city_profile_fallback",
    }
    print(f"    → fallback: ~{result['temperature_c']}°C, AC: {result['ac_importance']}")
    return result


# ══════════════════════════════════════════
#  TOOL 2 — Filter Tata Cars
# ══════════════════════════════════════════
def get_tata_cars(
    budget_min_lakhs: float,
    budget_max_lakhs: float,
    fuel_preference:  str = "any",
    min_seats:        int = 4,
) -> dict:
    """
    Filter TATA_CARS_DB by budget range, fuel type, and seat count.

    Args:
        budget_min_lakhs: Minimum budget in lakhs (e.g. 8.0)
        budget_max_lakhs: Maximum budget in lakhs (e.g. 16.0)
        fuel_preference:  'Petrol', 'Diesel', 'CNG', 'EV', or 'any'
        min_seats:        Minimum seats required (default 4)

    Returns:
        dict with total_matches and list of matching_cars with full specs
    """
    print(
        f"  [TOOL] get_tata_cars("
        f"budget={budget_min_lakhs}–{budget_max_lakhs}L, "
        f"fuel={fuel_preference}, seats>={min_seats})"
    )

    matching = []
    for name, s in TATA_CARS_DB.items():
        # Budget: at least one variant must overlap
        if s["price_min"] > budget_max_lakhs:
            continue
        if s["price_max"] < budget_min_lakhs:
            continue

        # Fuel filter
        if fuel_preference.lower() not in ("any", "no preference"):
            if not any(fuel_preference.lower() in f.lower() for f in s["fuel_types"]):
                continue

        # Seats filter
        if s["seats"] < min_seats:
            continue

        matching.append({
            "name":             name,
            "segment":          s["segment"],
            "price_range":      f"₹{s['price_min']}–{s['price_max']} Lakhs",
            "price_min":        s["price_min"],
            "price_max":        s["price_max"],
            "fuel_types":       s["fuel_types"],
            "mileage_kmpl":     s["mileage_kmpl"],
            "ev_range_km":      s["ev_range_km"],
            "power_ps":         s["power_ps"],
            "boot_litres":      s["boot_litres"],
            "seats":            s["seats"],
            "ground_clearance": s["ground_clearance"],
            "safety_stars":     s["safety_rating"],
            "ac_quality":       s["ac_quality"],
            "best_for":         s["best_for"],
            "not_good_for":     s["not_good_for"],
            "emi_approx":       s["emi_min"],
            "usp":              s["usp"],
        })

    print(f"    → {len(matching)} cars matched")
    return {
        "total_matches":   len(matching),
        "search_criteria": {
            "budget":    f"{budget_min_lakhs}–{budget_max_lakhs} Lakhs",
            "fuel":      fuel_preference,
            "min_seats": min_seats,
        },
        "matching_cars": matching,
    }


# ══════════════════════════════════════════
#  TOOL 3 — Fuel Price
# ══════════════════════════════════════════
def get_fuel_price(city: str, fuel_type: str = "Petrol") -> dict:
    """
    Get today's petrol / diesel / CNG price per litre in an Indian city.
    Uses static reference prices (Feb 2026). Monthly cost is estimated
    based on 1,500 km/month average Indian driving.

    Args:
        city:      Indian city name
        fuel_type: 'Petrol', 'Diesel', or 'CNG'

    Returns:
        dict with price_per_litre, monthly_cost_estimate, annual_cost_estimate
    """
    print(f"  [TOOL] get_fuel_price(city='{city}', fuel_type='{fuel_type}')")

    # Normalise fuel key
    fuel_key = {
        "petrol": "Petrol",
        "diesel": "Diesel",
        "cng":    "CNG",
    }.get(fuel_type.lower(), "Petrol")

    # Look up city (case-insensitive partial match)
    prices   = REFERENCE_FUEL_PRICES.get(fuel_key, REFERENCE_FUEL_PRICES["Petrol"])
    city_key = next(
        (k for k in prices if k.lower() in city.lower()),
        "DEFAULT"
    )
    price_per_litre = prices[city_key]

    # Monthly cost estimate
    monthly_km    = 1500
    avg_mileage   = 26.0 if fuel_key == "CNG" else 18.0 if fuel_key == "Diesel" else 17.0
    monthly_cost  = (monthly_km / avg_mileage) * price_per_litre

    print(f"    → {fuel_key} in {city}: ₹{price_per_litre}/L  est. ₹{round(monthly_cost)}/month")
    return {
        "city":                   city,
        "fuel_type":              fuel_key,
        "price_per_litre":        price_per_litre,
        "currency":               "INR",
        "source":                 "reference_data_feb2026",
        "monthly_cost_estimate":  round(monthly_cost),
        "annual_cost_estimate":   round(monthly_cost * 12),
        "assumptions":            f"{monthly_km} km/month, {avg_mileage} kmpl avg",
    }


# ══════════════════════════════════════════
#  TOOL 4 — Total Cost of Ownership
# ══════════════════════════════════════════
def calculate_tco(
    car_name:        str,
    city:            str,
    daily_km:        float,
    ownership_years: int   = 5,
    fuel_type:       str   = "Petrol",
) -> dict:
    """
    Calculate N-year Total Cost of Ownership for a specific Tata car.
    Covers: EMI (8.5%, 7-year loan, 20% down) + fuel + insurance + maintenance.

    Args:
        car_name:        Exact Tata car name e.g. 'Tata Nexon'
        city:            City for fuel price lookup
        daily_km:        Average km driven per day
        ownership_years: Years to project (default 5)
        fuel_type:       'Petrol', 'Diesel', 'CNG', or 'EV'

    Returns:
        dict with monthly_breakdown, total cost, estimated resale
    """
    print(
        f"  [TOOL] calculate_tco("
        f"car='{car_name}', city='{city}', "
        f"daily_km={daily_km}, fuel={fuel_type})"
    )

    # Fuzzy name match
    match = next(
        (k for k in TATA_CARS_DB
         if car_name.lower() in k.lower() or k.lower() in car_name.lower()),
        None
    )
    if not match:
        err = f"Car '{car_name}' not found. Available: {list(TATA_CARS_DB.keys())}"
        print(f"    → ERROR: {err}")
        return {"error": err}

    s         = TATA_CARS_DB[match]
    price_inr = s["price_min"] * 100_000   # base variant

    # ── EMI: 8.5% annual, 7-year loan, 20% down ──
    down_pmt  = price_inr * 0.20
    loan_amt  = price_inr * 0.80
    r_monthly = 0.085 / 12
    n_months  = 7 * 12
    emi       = loan_amt * (r_monthly * (1 + r_monthly) ** n_months) / \
                          ((1 + r_monthly) ** n_months - 1)

    # ── Monthly fuel cost ──
    monthly_km = daily_km * 30
    if fuel_type.upper() == "EV":
        # ~15 kWh/100 km, ₹7/kWh home charging
        monthly_fuel_cost = (monthly_km / 100) * 15 * 7
        fuel_note         = "EV: ₹7/kWh home charging, 15 kWh/100 km"
    else:
        fd                = get_fuel_price(city, fuel_type)
        ppl               = fd["price_per_litre"]
        mileage           = s["mileage_kmpl"] or 18.0
        monthly_fuel_cost = (monthly_km / mileage) * ppl
        fuel_note         = f"₹{ppl}/L at {mileage} kmpl"

    # ── Insurance: ~3% IDV year 1 ──
    monthly_insurance = (price_inr * 0.03) / 12

    # ── Maintenance: ~₹10,000 per 10,000 km ──
    annual_km         = daily_km * 365
    services_per_year = max(1, annual_km / 10_000)
    monthly_maint     = (services_per_year * 10_000) / 12

    # ── Totals ──
    monthly_total = emi + monthly_fuel_cost + monthly_insurance + monthly_maint
    annual_total  = monthly_total * 12
    total_cost    = (annual_total * ownership_years) + down_pmt

    # ── Depreciation: 20% yr1, 15% yr2-3, 10% yr4-5 ──
    resale_5yr    = price_inr * 0.80 * 0.85 * 0.85 * 0.90 * 0.90

    print(f"    → {match}: ₹{round(monthly_total):,}/month total")
    return {
        "car":                            match,
        "variant":                        "Base variant",
        "ex_showroom_price":              f"₹{s['price_min']:.2f} Lakhs",
        "down_payment":                   f"₹{down_pmt:,.0f}",
        "monthly_breakdown": {
            "emi_7yr_8.5pct":             round(emi),
            "fuel_cost":                  round(monthly_fuel_cost),
            "insurance":                  round(monthly_insurance),
            "maintenance":                round(monthly_maint),
            "total_monthly":              round(monthly_total),
        },
        "annual_total":                   round(annual_total),
        f"total_{ownership_years}yr_cost": round(total_cost),
        "estimated_resale_5yr":           f"₹{resale_5yr/100_000:.2f} Lakhs",
        "fuel_note":                      fuel_note,
        "daily_km_assumption":            daily_km,
    }


# ══════════════════════════════════════════
#  DISPATCHER — called by both agents
# ══════════════════════════════════════════
TOOL_MAP = {
    "get_city_weather": get_city_weather,
    "get_tata_cars":    get_tata_cars,
    "get_fuel_price":   get_fuel_price,
    "calculate_tco":    calculate_tco,
}

def dispatch(tool_name: str, args: dict) -> str:
    """
    Execute a tool by name and return the result as a JSON string.
    Returns an error JSON if the tool name is unknown or the call fails.
    """
    if tool_name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool: '{tool_name}'. Available: {list(TOOL_MAP.keys())}"})
    try:
        result = TOOL_MAP[tool_name](**args)
        return json.dumps(result, ensure_ascii=False, default=str)
    except TypeError as e:
        return json.dumps({"error": f"Bad arguments for {tool_name}: {e}", "args_received": args})
    except Exception as e:
        return json.dumps({"error": str(e), "tool": tool_name})


# ══════════════════════════════════════════
#  STANDALONE TEST — run: python tools.py
# ══════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 55)
    print("  tools.py — standalone test")
    print("=" * 55)

    print("\n[1] Weather — Mumbai")
    w = get_city_weather("Mumbai")
    print(f"    {w['temperature_c']}°C  {w['humidity_pct']}% humidity  AC: {w['ac_importance']}")

    print("\n[2] Car filter — ₹10–16L, Petrol, 4+ seats")
    c = get_tata_cars(10.0, 16.0, "Petrol")
    print(f"    {c['total_matches']} cars: {[x['name'] for x in c['matching_cars']]}")

    print("\n[3] Fuel price — Hyderabad Petrol")
    f = get_fuel_price("Hyderabad", "Petrol")
    print(f"    ₹{f['price_per_litre']}/L  → ₹{f['monthly_cost_estimate']}/month")

    print("\n[4] TCO — Tata Nexon, Bangalore, 35 km/day, Petrol")
    t = calculate_tco("Tata Nexon", "Bangalore", 35, 5, "Petrol")
    mb = t["monthly_breakdown"]
    print(f"    EMI ₹{mb['emi_7yr_8.5pct']:,}  Fuel ₹{mb['fuel_cost']:,}  Total ₹{mb['total_monthly']:,}/mo")

    print("\n[5] Dispatcher test — unknown tool")
    print(f"    {dispatch('nonexistent_tool', {})}")

    print("\n✅ All tools working!")
