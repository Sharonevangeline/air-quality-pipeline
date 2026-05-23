import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

logger = logging.getLogger(__name__)


def send_email(subject: str, body: str):
    """Send a plain-text alert email via Gmail SMTP."""
    sender = os.getenv("ALERT_EMAIL_FROM")
    recipient = os.getenv("ALERT_EMAIL_TO")
    password = os.getenv("ALERT_EMAIL_PASSWORD")

    if not all([sender, recipient, password]):
        logger.warning("Email credentials not configured — skipping alert")
        return

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        logger.info("Alert email sent: %s", subject)
    except Exception as e:
        logger.error("Failed to send alert email: %s", e)


def check_and_send_rain_alerts(weather_records: list[dict]):
    """
    Send one consolidated rain alert email listing all cities
    where rain is expected in the next 24 hours.
    """
    rainy_cities = [
        r for r in weather_records if r.get("rain_expected")
    ]

    if not rainy_cities:
        logger.info("No rain alerts to send today")
        return

    lines = [
        f"Rain Alert Summary — {date.today()}",
        "=" * 40,
        "The following cities have rain expected in the next 24 hours:",
        "",
    ]

    for r in rainy_cities:
        lines.append(f"City            : {r['city']}")
        lines.append(f"Rain probability: {r['rain_probability']}%")
        lines.append(f"Condition       : {r['condition']}")
        lines.append(f"Temperature     : {r['temperature']} C")
        lines.append(f"Humidity        : {r['humidity']}%")
        lines.append("-" * 40)

    body = "\n".join(lines)
    send_email(
        subject=f"[Pipeline] Rain expected in {len(rainy_cities)} cities — {date.today()}",
        body=body,
    )


def check_and_send_aqi_alerts(aq_records: list[dict]):
    """
    Send one consolidated AQI alert email listing all cities
    with Unhealthy or worse air quality.
    """
    bad_cities = [
        r for r in aq_records
        if r.get("aqi_category") in (
            "Unhealthy", "Very Unhealthy", "Hazardous"
        )
    ]

    if not bad_cities:
        logger.info("No AQI alerts to send today")
        return

    lines = [
        f"Air Quality Alert Summary — {date.today()}",
        "=" * 40,
        "The following cities have unhealthy air quality:",
        "",
    ]

    for r in bad_cities:
        lines.append(f"City        : {r['city']}")
        lines.append(f"AQI category: {r['aqi_category']}")
        lines.append(f"PM2.5       : {r['pm25']} ug/m3")
        lines.append(f"PM10        : {r['pm10']} ug/m3")
        lines.append("-" * 40)

    body = "\n".join(lines)
    send_email(
        subject=f"[Pipeline] Poor air quality in {len(bad_cities)} cities — {date.today()}",
        body=body,
    )


def send_failure_alert(task_name: str, error_message: str):
    """Send an alert when a pipeline task fails."""
    body = "\n".join([
        f"Pipeline Failure — {date.today()}",
        "=" * 40,
        f"Task     : {task_name}",
        f"Error    : {error_message}",
        "",
        "Check Airflow logs for full traceback.",
    ])
    send_email(
        subject=f"[Pipeline] FAILURE in task: {task_name} — {date.today()}",
        body=body,
    )