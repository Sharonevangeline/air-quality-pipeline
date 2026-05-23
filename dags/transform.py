import logging
from datetime import datetime
from datetime import datetime


logger = logging.getLogger(__name__)


def get_aqi_category(pm25: float) -> str:
    """Map PM2.5 value to AQI category per WHO guidelines."""
    if pm25 is None:
        return "Unknown"
    if pm25 <= 12:
        return "Good"
    if pm25 <= 35.4:
        return "Moderate"
    if pm25 <= 55.4:
        return "Unhealthy for Sensitive Groups"
    if pm25 <= 150.4:
        return "Unhealthy"
    if pm25 <= 250.4:
        return "Very Unhealthy"
    return "Hazardous"


def transform_air_quality(raw_records: list[dict]) -> list[dict]:
    """
    Clean and normalise raw OpenAQ records.
    Extracts individual pollutant readings per city.
    """
    transformed = []
    seen = set()

    for record in raw_records:
        city = record.get("city")
        measurements = record.get("measurements", [])

        pollutants = {"pm25": None, "pm10": None, "no2": None, "co": None}
        measured_at = None

        for m in measurements:
            parameter = m.get("parameter", "").lower().replace(".", "")
            value = m.get("value")
            last_updated = m.get("lastUpdated")

            if parameter == "pm25" and value is not None and value >= 0:
                pollutants["pm25"] = round(value, 2)
            elif parameter == "pm10" and value is not None and value >= 0:
                pollutants["pm10"] = round(value, 2)
            elif parameter == "no2" and value is not None and value >= 0:
                pollutants["no2"] = round(value, 2)
            elif parameter == "co" and value is not None and value >= 0:
                pollutants["co"] = round(value, 2)

            if last_updated and measured_at is None:
                try:
                    measured_at = datetime.fromisoformat(
                        last_updated.replace("Z", "+00:00")
                    )
                except ValueError:
                    measured_at = datetime.utcnow()

        dedup_key = (city, measured_at)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        transformed.append({
            "city": city,
            "pm25": pollutants["pm25"],
            "pm10": pollutants["pm10"],
            "no2": pollutants["no2"],
            "co": pollutants["co"],
            "aqi_category": get_aqi_category(pollutants["pm25"]),
            "measured_at": measured_at or datetime.utcnow(),
        })

    logger.info("Transformed %d air quality records", len(transformed))
    return transformed


def transform_weather(raw_records: list[dict]) -> list[dict]:
    """
    Clean and normalise raw OpenWeatherMap forecast records.
    Flags cities with rain expected in the next 24 hours.
    """
    transformed = []

    for record in raw_records:
        city = record.get("city")
        forecasts = record.get("forecasts", [])

        if not forecasts:
            continue

        current = forecasts[0]
        main = current.get("main", {})
        weather = current.get("weather", [{}])[0]
        rain = current.get("rain", {})

        rain_probability = round(current.get("pop", 0) * 100, 1)
        rain_volume = rain.get("3h", 0)
        rain_expected = rain_probability > 60 or rain_volume > 0

        try:
            forecast_time = datetime.utcfromtimestamp(current.get("dt", 0))
        except (TypeError, ValueError):
            forecast_time = datetime.utcnow()

        transformed.append({
            "city": city,
            "temperature": round(main.get("temp", 0), 1),
            "feels_like": round(main.get("feels_like", 0), 1),
            "humidity": main.get("humidity", 0),
            "wind_speed": round(current.get("wind", {}).get("speed", 0), 1),
            "condition": weather.get("description", "unknown").title(),
            "rain_probability": rain_probability,
            "rain_expected": rain_expected,
            "forecast_time": forecast_time,
        })

    logger.info("Transformed %d weather records", len(transformed))
    return transformed
