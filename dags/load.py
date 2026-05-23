import os
import logging
import psycopg2
from datetime import datetime, date

logger = logging.getLogger(__name__)


def get_connection():
    """Return a psycopg2 connection to the pipeline database."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname="pipeline",
        user=os.getenv("POSTGRES_USER", "airflow"),
        password=os.getenv("POSTGRES_PASSWORD", "airflow"),
    )


def load_air_quality(records: list[dict]) -> int:
    """Insert cleaned air quality records. Returns count inserted."""
    if not records:
        logger.warning("No air quality records to load")
        return 0

    sql = """
        INSERT INTO air_quality
            (city, pm25, pm10, no2, co, aqi_category, measured_at)
        VALUES
            (%(city)s, %(pm25)s, %(pm10)s, %(no2)s, %(co)s,
             %(aqi_category)s, %(measured_at)s)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()
        logger.info("Loaded %d air quality records", len(records))
        return len(records)
    except Exception as e:
        conn.rollback()
        logger.error("Failed to load air quality records: %s", e)
        raise
    finally:
        conn.close()


def load_weather(records: list[dict]) -> int:
    """Insert cleaned weather forecast records. Returns count inserted."""
    if not records:
        logger.warning("No weather records to load")
        return 0

    sql = """
        INSERT INTO weather_forecast
            (city, temperature, feels_like, humidity, wind_speed,
             condition, rain_probability, rain_expected, forecast_time)
        VALUES
            (%(city)s, %(temperature)s, %(feels_like)s, %(humidity)s,
             %(wind_speed)s, %(condition)s, %(rain_probability)s,
             %(rain_expected)s, %(forecast_time)s)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()
        logger.info("Loaded %d weather records", len(records))
        return len(records)
    except Exception as e:
        conn.rollback()
        logger.error("Failed to load weather records: %s", e)
        raise
    finally:
        conn.close()


def log_pipeline_run(task_name: str, status: str,
                     records: int = 0, error: str = None):
    """Write a pipeline run entry to pipeline_logs table."""
    sql = """
        INSERT INTO pipeline_logs
            (run_date, task_name, status, records_processed, error_message)
        VALUES (%s, %s, %s, %s, %s)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (date.today(), task_name, status, records, error))
        conn.commit()
    except Exception as e:
        logger.error("Failed to write pipeline log: %s", e)
    finally:
        conn.close()
