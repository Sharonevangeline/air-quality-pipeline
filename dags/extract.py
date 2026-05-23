import os
import requests
import logging
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


logger = logging.getLogger(__name__)

CITIES = [
    {"name": "Hyderabad", "lat": 17.3850, "lon": 78.4867},
    {"name": "Delhi",     "lat": 28.6139, "lon": 77.2090},
    {"name": "Mumbai",    "lat": 19.0760, "lon": 72.8777},
    {"name": "Bangalore", "lat": 12.9716, "lon": 77.5946},
    {"name": "Chennai",   "lat": 13.0827, "lon": 80.2707},
    {"name": "Kolkata",   "lat": 22.5726, "lon": 88.3639},
    {"name": "Pune",      "lat": 18.5204, "lon": 73.8567},
    {"name": "Ahmedabad", "lat": 23.0225, "lon": 72.5714},
    {"name": "Jaipur",    "lat": 26.9124, "lon": 75.7873},
    {"name": "Lucknow",   "lat": 26.8467, "lon": 80.9462},
]

def fetch_air_quality() -> list[dict]:
    """
    Fetch real-time AQI data for all cities from WAQI API.
    Returns a list of raw measurement dicts.
    """
    api_key = os.getenv("WAQI_API_KEY")
    if not api_key:
        raise ValueError("WAQI_API_KEY not set in environment")

    results = []

    for city in CITIES:
        try:
            response = requests.get(
                f"https://api.waqi.info/feed/{city['name'].lower()}/",
                params={"token": api_key},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                logger.warning("No AQ data for %s: %s", city["name"], data.get("data"))
                continue

            d = data["data"]
            iaqi = d.get("iaqi", {})

            measurements = [
                {"parameter": "pm25", "value": iaqi.get("pm25", {}).get("v"), "lastUpdated": d["time"].get("iso")},
                {"parameter": "pm10", "value": iaqi.get("pm10", {}).get("v"), "lastUpdated": d["time"].get("iso")},
                {"parameter": "no2",  "value": iaqi.get("no2",  {}).get("v"), "lastUpdated": d["time"].get("iso")},
                {"parameter": "co",   "value": iaqi.get("co",   {}).get("v"), "lastUpdated": d["time"].get("iso")},
            ]

            record = {
                "city": city["name"],
                "location": d.get("city", {}).get("name", city["name"]),
                "measurements": measurements,
                "fetched_at": datetime.now(tz=IST).isoformat(),
            }
            results.append(record)
            logger.info("Fetched AQ data for %s — AQI: %s", city["name"], d.get("aqi"))

        except requests.RequestException as e:
            logger.error("Failed to fetch AQ data for %s: %s", city["name"], e)
            continue

    logger.info("Fetched air quality data for %d locations", len(results))
    return results

def fetch_weather() -> list[dict]:
    """
    Fetch current weather and 24-hour rain forecast for all cities
    from OpenWeatherMap API.
    Returns a list of raw weather dicts.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise ValueError("OPENWEATHER_API_KEY not set in environment")

    results = []
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"

    for city in CITIES:
        try:
            response = requests.get(
                forecast_url,
                params={
                    "lat": city["lat"],
                    "lon": city["lon"],
                    "appid": api_key,
                    "units": "metric",
                    "cnt": 8,
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            record = {
                "city": city["name"],
                "lat": city["lat"],
                "lon": city["lon"],
                "forecasts": data.get("list", []),
                "fetched_at": datetime.now(tz=IST).isoformat(),
            }
            results.append(record)

        except requests.RequestException as e:
            logger.error("Failed to fetch weather for %s: %s", city["name"], e)
            continue

    logger.info("Fetched weather data for %d cities", len(results))
    return results
