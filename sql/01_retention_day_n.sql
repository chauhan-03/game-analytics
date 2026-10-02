-- Day-N retention: share of players registered 2020-01-01..2020-09-22 who logged in on
-- exactly calendar day N after registering. Only players who have had N full days count.
-- Days are whole UTC days since the epoch (timestamp / 86400), registration day = day 0.
WITH params AS (
    SELECT CAST(strftime('%s', '2020-01-01') AS INTEGER) / 86400 AS start_day,
           CAST(strftime('%s', '2020-09-22') AS INTEGER) / 86400 AS last_day
),
cohort AS (
    SELECT r.uid, r.reg_ts / 86400 AS reg_day
    FROM registrations r, params p
    WHERE r.reg_ts / 86400 BETWEEN p.start_day AND p.last_day
),
active AS (
    SELECT DISTINCT l.uid, l.auth_ts / 86400 AS day
    FROM logins l JOIN cohort c USING (uid)
),
days(n) AS (VALUES (1), (3), (7), (14), (30))
SELECT
    d.n AS day_n,
    (SELECT COUNT(*) FROM cohort c, params p WHERE c.reg_day + d.n <= p.last_day) AS eligible,
    (SELECT COUNT(*) FROM active a JOIN cohort c USING (uid), params p
      WHERE a.day = c.reg_day + d.n AND a.day <= p.last_day) AS retained,
    ROUND(1.0 * (SELECT COUNT(*) FROM active a JOIN cohort c USING (uid), params p
                  WHERE a.day = c.reg_day + d.n AND a.day <= p.last_day)
              / (SELECT COUNT(*) FROM cohort c, params p WHERE c.reg_day + d.n <= p.last_day), 6) AS retention
FROM days d
ORDER BY d.n;
