DROP VIEW IF EXISTS public.jumpable_time;
CREATE VIEW public.jumpable_time AS
SELECT
    f.dropzone_id,
    (f.timestamp AT TIME ZONE 'Europe/Zurich') AT TIME ZONE 'UTC' AS hour_utc,
    f.temperature_2m_c,
    f.wind_speed_10m_mps,
    f.wind_gusts_10m_mps,
    f.cloud_cover_low_percent,
    f.precipitation_mm,
    f.visibility_m,
    f.wind_speed_850hpa_mps,
    f.wind_speed_700hpa_mps,
    (f.temperature_2m_c       BETWEEN r.min_temp       AND r.max_temp)       AS temp_ok,
    (f.wind_speed_10m_mps     BETWEEN r.min_wind       AND r.max_wind)       AS wind_ok,
    (f.wind_gusts_10m_mps     <= r.max_gust)                                 AS gust_ok,
    (f.cloud_cover_low_percent BETWEEN r.min_cloud_low AND r.max_cloud_low)  AS cloud_ok,
    (f.precipitation_mm       <= r.max_precip)                               AS precip_ok,
    (f.visibility_m           BETWEEN r.min_visibility AND r.max_visibility) AS visibility_ok,
    (f.wind_speed_850hpa_mps  BETWEEN r.min_wind_850   AND r.max_wind_850)   AS wind_850_ok,
    (f.wind_speed_700hpa_mps  BETWEEN r.min_wind_700   AND r.max_wind_700)   AS wind_700_ok,
    (
        f.temperature_2m_c        BETWEEN r.min_temp       AND r.max_temp
        AND f.wind_speed_10m_mps  BETWEEN r.min_wind       AND r.max_wind
        AND f.wind_gusts_10m_mps  <= r.max_gust
        AND f.cloud_cover_low_percent BETWEEN r.min_cloud_low AND r.max_cloud_low
        AND f.precipitation_mm    <= r.max_precip
        AND f.visibility_m        BETWEEN r.min_visibility AND r.max_visibility
        AND f.wind_speed_850hpa_mps BETWEEN r.min_wind_850 AND r.max_wind_850
        AND f.wind_speed_700hpa_mps BETWEEN r.min_wind_700 AND r.max_wind_700
    ) AS jumpable
FROM public.weather_forecast f
CROSS JOIN public.jumpability_range r;
