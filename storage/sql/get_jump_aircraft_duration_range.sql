
WITH quartiles AS (
    SELECT
        PERCENTILE_CONT(0.25)
            WITHIN GROUP (ORDER BY duration) AS q1,
        PERCENTILE_CONT(0.75)
            WITHIN GROUP (ORDER BY duration) AS q3
    FROM public.flight_history
),
bounds AS (
    SELECT
        q1 - 1.5 * (q3 - q1) AS lower_bound,
        q3 + 1.5 * (q3 - q1) AS upper_bound
    FROM quartiles
),
base_flights AS (
    SELECT f.*
    FROM public.flight_history f
    CROSS JOIN bounds b
    WHERE f.duration BETWEEN b.lower_bound
                         AND b.upper_bound
),
base_flight_duration AS (
    SELECT
        AVG(f.duration) AS average_duration,
        MIN(f.duration) AS min_duration,
        MAX(f.duration) AS max_duration
    FROM base_flights f
    INNER JOIN public.jump_aircraft j
        ON f.callsign = j.callsign_id
    WHERE f.departure_airport = f.arrival_airport
)

SELECT
    average_duration,
    min_duration,
    max_duration,
    ((average_duration - min_duration) +
     (max_duration - average_duration)) / 2.0
        AS average_offset
FROM base_flight_duration;
