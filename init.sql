CREATE TABLE IF NOT EXISTS weather_data (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(9, 6) NOT NULL,
    temperature DECIMAL(5, 2),
    windspeed DECIMAL(5, 2),
    winddirection INTEGER,
    weathercode INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);