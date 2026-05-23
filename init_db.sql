CREATE DATABASE pipeline;

\c pipeline;

CREATE TABLE IF NOT EXISTS air_quality (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(10) DEFAULT 'IN',
    pm25 FLOAT,
    pm10 FLOAT,
    no2 FLOAT,
    co FLOAT,
    aqi_category VARCHAR(50),
    measured_at TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS weather_forecast (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    temperature FLOAT,
    feels_like FLOAT,
    humidity INTEGER,
    wind_speed FLOAT,
    condition VARCHAR(100),
    rain_probability FLOAT,
    rain_expected BOOLEAN DEFAULT FALSE,
    forecast_time TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_logs (
    id SERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    task_name VARCHAR(100),
    status VARCHAR(20),
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_aq_city_date ON air_quality(city, measured_at);
CREATE INDEX idx_weather_city_date ON weather_forecast(city, forecast_time);
