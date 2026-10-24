DROP VIEW IF EXISTS public.jumpability_range;
CREATE OR REPLACE VIEW public.jumpability_range AS
WITH jump_flight_history AS (
	SELECT * FROM public.flight_history
		WHERE departure_airport = arrival_airport 
			AND  callsign IN (SELECT callsign_id FROM public.jump_aircraft)
		
)
SELECT
    MIN(w.temperature_2m_c)        AS min_temp,
    MAX(w.temperature_2m_c)        AS max_temp,
    MIN(w.wind_speed_10m_mps)      AS min_wind,
    MAX(w.wind_speed_10m_mps)      AS max_wind,
    MAX(w.wind_gusts_10m_mps)      AS max_gust,
    MIN(w.cloud_cover_low_percent) AS min_cloud_low,
    MAX(w.cloud_cover_low_percent) AS max_cloud_low,
    MAX(w.precipitation_mm)        AS max_precip,
    MIN(w.visibility_m)            AS min_visibility,
    MAX(w.visibility_m)            AS max_visibility,
    MIN(w.wind_speed_850hpa_mps)   AS min_wind_850,
    MAX(w.wind_speed_850hpa_mps)   AS max_wind_850,
    MIN(w.wind_speed_700hpa_mps)   AS min_wind_700,
    MAX(w.wind_speed_700hpa_mps)   AS max_wind_700
FROM jump_flight_history f
LEFT JOIN public.weather_history w
  ON  w.dropzone_id = f.dropzone_id
  AND w.timestamp = date_trunc('hour', (f.timestamp AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Zurich')
