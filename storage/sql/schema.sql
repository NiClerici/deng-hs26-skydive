CREATE TABLE IF NOT EXISTS public.swiss_dropzone (
    dropzone_id TEXT PRIMARY KEY,  -- airfield ICAO code, e.g. LSGB
    fullname TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    elevation_m INTEGER
);

CREATE TABLE IF NOT EXISTS public.jump_aircraft (
    callsign_id TEXT PRIMARY KEY,
    dropzone_id TEXT NOT NULL REFERENCES public.swiss_dropzone(dropzone_id),
    icao24 TEXT  -- hex transponder code, e.g. 4b4488
);

CREATE TABLE IF NOT EXISTS public.weather_history (
    dropzone_id TEXT NOT NULL REFERENCES public.swiss_dropzone(dropzone_id),
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

CREATE TABLE IF NOT EXISTS public.flight_history (
    dropzone_id TEXT NOT NULL REFERENCES public.swiss_dropzone(dropzone_id),
    timestamp TIMESTAMP NOT NULL,
    icao24 TEXT NOT NULL,
    callsign TEXT NOT NULL,
    departure_airport TEXT,
    arrival_airport TEXT,
    duration INTEGER,
    PRIMARY KEY (dropzone_id, timestamp, icao24)
);
