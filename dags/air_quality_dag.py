import logging
from datetime import datetime, timedelta
from pendulum import timezone
from airflow import DAG
from airflow.operators.python import PythonOperator

from extract import fetch_air_quality, fetch_weather
from transform import transform_air_quality, transform_weather
from load import load_air_quality, load_weather, log_pipeline_run
from alerts import (
    check_and_send_rain_alerts,
    check_and_send_aqi_alerts,
    send_failure_alert,
)

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "sharon",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def run_extract_air_quality(**context):
    try:
        raw = fetch_air_quality()
        context["ti"].xcom_push(key="raw_aq", value=raw)
        log_pipeline_run("extract_air_quality", "SUCCESS", len(raw))
    except Exception as e:
        log_pipeline_run("extract_air_quality", "FAILED", error=str(e))
        send_failure_alert("extract_air_quality", str(e))
        raise


def run_extract_weather(**context):
    try:
        raw = fetch_weather()
        context["ti"].xcom_push(key="raw_weather", value=raw)
        log_pipeline_run("extract_weather", "SUCCESS", len(raw))
    except Exception as e:
        log_pipeline_run("extract_weather", "FAILED", error=str(e))
        send_failure_alert("extract_weather", str(e))
        raise

def run_transform_load_aq(**context):
    try:
        raw = context["ti"].xcom_pull(key="raw_aq", task_ids="extract_air_quality")
        cleaned = transform_air_quality(raw)
        count = load_air_quality(cleaned)
        # Convert datetime to string before XCom push
        serializable = [
            {**r, "measured_at": r["measured_at"].isoformat() if hasattr(r["measured_at"], "isoformat") else r["measured_at"]}
            for r in cleaned
        ]
        context["ti"].xcom_push(key="aq_records", value=serializable)
        log_pipeline_run("transform_load_air_quality", "SUCCESS", count)
    except Exception as e:
        log_pipeline_run("transform_load_air_quality", "FAILED", error=str(e))
        send_failure_alert("transform_load_air_quality", str(e))
        raise


def run_transform_load_weather(**context):
    try:
        raw = context["ti"].xcom_pull(key="raw_weather", task_ids="extract_weather")
        cleaned = transform_weather(raw)
        count = load_weather(cleaned)
        # Convert datetime to string before XCom push
        serializable = [
            {**r, "forecast_time": r["forecast_time"].isoformat() if hasattr(r["forecast_time"], "isoformat") else r["forecast_time"]}
            for r in cleaned
        ]
        context["ti"].xcom_push(key="weather_records", value=serializable)
        log_pipeline_run("transform_load_weather", "SUCCESS", count)
    except Exception as e:
        log_pipeline_run("transform_load_weather", "FAILED", error=str(e))
        send_failure_alert("transform_load_weather", str(e))
        raise


def run_alerts(**context):
    try:
        aq = context["ti"].xcom_pull(key="aq_records",
                                     task_ids="transform_load_air_quality")
        weather = context["ti"].xcom_pull(key="weather_records",
                                          task_ids="transform_load_weather")
        check_and_send_aqi_alerts(aq or [])
        check_and_send_rain_alerts(weather or [])
        log_pipeline_run("alerts", "SUCCESS")
    except Exception as e:
        log_pipeline_run("alerts", "FAILED", error=str(e))
        send_failure_alert("alerts", str(e))
        raise


with DAG(
    dag_id="air_quality_weather_pipeline",
    default_args=DEFAULT_ARGS,
    description="Daily ETL pipeline for air quality and weather across 10 Indian cities",
    schedule="0 7 * * *",
    start_date=datetime(2025, 1, 1, tzinfo=timezone("Asia/Kolkata")),
    catchup=False,
    tags=["air-quality", "weather", "etl"],
) as dag:

    extract_aq = PythonOperator(
        task_id="extract_air_quality",
        python_callable=run_extract_air_quality,
    )

    extract_weather = PythonOperator(
        task_id="extract_weather",
        python_callable=run_extract_weather,
    )

    transform_load_aq = PythonOperator(
        task_id="transform_load_air_quality",
        python_callable=run_transform_load_aq,
    )

    transform_load_weather = PythonOperator(
        task_id="transform_load_weather",
        python_callable=run_transform_load_weather,
    )

    send_alerts = PythonOperator(
        task_id="send_alerts",
        python_callable=run_alerts,
    )

    # DAG dependency chain
    # Extract runs in parallel, then transform/load, then alerts
    [extract_aq, extract_weather] >> transform_load_aq
    [extract_aq, extract_weather] >> transform_load_weather
    [transform_load_aq, transform_load_weather] >> send_alerts