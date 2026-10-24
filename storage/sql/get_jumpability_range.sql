CREATE OR REPLACE VIEW public.jumpability_range AS
WITH jump_flights AS (
	SELECT f.* FROM public.flight_history f
		WHERE f.departure_airport = f.arrival_airport
			AND EXISTS (SELECT 1 FROM public.jump_aircraft j
						WHERE j.icao24 = f.icao24 AND j.dropzone_id = f.dropzone_id)
),
duration_fences AS (
	SELECT dropzone_id,
		q1 - 1.5 * (q3 - q1) AS lower_bound,
		q3 + 1.5 * (q3 - q1) AS upper_bound
	FROM (
		SELECT dropzone_id,
			percentile_cont(0.25) WITHIN GROUP (ORDER BY duration) AS q1,
			percentile_cont(0.75) WITHIN GROUP (ORDER BY duration) AS q3
		FROM jump_flights
		GROUP BY dropzone_id
	) q
),
jump_hours AS (
	SELECT DISTINCT f.dropzone_id,
		date_trunc('hour', (f.timestamp AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Zurich') AS hour_local
	FROM jump_flights f
	JOIN duration_fences d ON d.dropzone_id = f.dropzone_id
	WHERE f.duration BETWEEN d.lower_bound AND d.upper_bound
)
SELECT
    percentile_cont(0.05) WITHIN GROUP (ORDER BY w.temperature_2m_c)        AS min_temp,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY w.temperature_2m_c)        AS max_temp,
    percentile_cont(0.05) WITHIN GROUP (ORDER BY w.wind_speed_10m_mps)      AS min_wind,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY w.wind_speed_10m_mps)      AS max_wind,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY w.wind_gusts_10m_mps)      AS max_gust,
    percentile_cont(0.05) WITHIN GROUP (ORDER BY w.cloud_cover_low_percent) AS min_cloud_low,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY w.cloud_cover_low_percent) AS max_cloud_low,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY w.precipitation_mm)        AS max_precip,
    percentile_cont(0.05) WITHIN GROUP (ORDER BY w.visibility_m)            AS min_visibility,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY w.visibility_m)            AS max_visibility,
    percentile_cont(0.05) WITHIN GROUP (ORDER BY w.wind_speed_850hpa_mps)   AS min_wind_850,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY w.wind_speed_850hpa_mps)   AS max_wind_850,
    percentile_cont(0.05) WITHIN GROUP (ORDER BY w.wind_speed_700hpa_mps)   AS min_wind_700,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY w.wind_speed_700hpa_mps)   AS max_wind_700
FROM jump_hours h
JOIN public.weather_history w
  ON  w.dropzone_id = h.dropzone_id
  AND w.timestamp = h.hour_local;
