CREATE TABLE IF NOT EXISTS public.swiss_dropzone (
    dropzone_id INTEGER PRIMARY KEY,
    fullname TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    elevation_m INTEGER
);

CREATE TABLE IF NOT EXISTS public.jump_aircraft (
    registration_id TEXT PRIMARY KEY,
    dropzone_id INTEGER NOT NULL REFERENCES public.swiss_dropzone(dropzone_id),
    icao24 INTEGER
);

CREATE TABLE IF NOT EXISTS public.weather_history (
    dropzone_id INTEGER NOT NULL REFERENCES public.swiss_dropzone(dropzone_id),
    timestamp TIMESTAMP NOT NULL,
    temperature_2m_c DOUBLE PRECISION,
    wind_speed_10m_mps DOUBLE PRECISION,
    wind_gusts_10m_mps DOUBLE PRECISION,
    cloud_cover_low_percent DOUBLE PRECISION,
    precipitation_mm DOUBLE PRECISION,
    visibility_m DOUBLE PRECISION,
    wind_speed_850hpa_mps DOUBLE PRECISION,
    wind_speed_700hpa_mps DOUBLE PRECISION,
    PRIMARY KEY (dropzone_id, timestamp)
);
