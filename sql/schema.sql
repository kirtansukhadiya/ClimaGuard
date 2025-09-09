CREATE TABLE IF NOT EXISTS weather_raw (
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(100),
    ts TIMESTAMP NOT NULL,
    temp_c FLOAT NOT NULL,
    min_temp_c FLOAT NOT NULL, 
    max_temp_c FLOAT NOT NULL,
    wind_speed FLOAT NOT NULL,
    humidity INT,
    aqi INT,
    pm25 FLOAT,
    pm10 FLOAT,
    weather_description VARCHAR(255),
    wind_direction INT,
    cloudiness INT,
    co FLOAT,
    no_ FLOAT,
    no2 FLOAT,
    o3 FLOAT,
    so2 FLOAT,
    nh3 FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weather_daily(
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(100),
    date DATE NOT NULL,
    min_temp_c FLOAT NOT NULL,
    avg_temp_c FLOAT NOT NULL,
    wind_speed FLOAT NOT NULL,
    humidity FLOAT,
    wind_chill FLOAT,
    mean_aqi FLOAT,
    risk_level VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions(
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(100),
    date DATE NOT NULL,
    predicted_risk VARCHAR(20),
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);