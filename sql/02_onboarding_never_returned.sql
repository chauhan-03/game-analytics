-- Onboarding drop-off: of 2020 players with a full 30 days of history, how many never
-- came back after registration day, and how many came back within 7 days.
WITH params AS (
    SELECT CAST(strftime('%s', '2020-01-01') AS INTEGER) / 86400 AS start_day,
           CAST(strftime('%s', '2020-09-22') AS INTEGER) / 86400 AS last_day
),
mature AS (
    SELECT r.uid, r.reg_ts / 86400 AS reg_day
    FROM registrations r, params p
    WHERE r.reg_ts / 86400 BETWEEN p.start_day AND p.last_day - 30
),
first_return AS (
    SELECT m.uid, MIN(l.auth_ts / 86400 - m.reg_day) AS first_day
    FROM mature m JOIN logins l USING (uid)
    WHERE l.auth_ts / 86400 - m.reg_day BETWEEN 1 AND 30
    GROUP BY m.uid
)
SELECT
    (SELECT COUNT(*) FROM mature) AS players,
    ROUND(1 - 1.0 * (SELECT COUNT(*) FROM first_return) / (SELECT COUNT(*) FROM mature), 6) AS never_returned_30d,
    ROUND(1.0 * (SELECT COUNT(*) FROM first_return WHERE first_day <= 7) / (SELECT COUNT(*) FROM mature), 6) AS returned_within_7d;
