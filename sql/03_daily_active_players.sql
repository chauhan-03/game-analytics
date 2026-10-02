-- Daily active players (DAU) and new registrations per day, 2020.
WITH params AS (
    SELECT CAST(strftime('%s', '2020-01-01') AS INTEGER) / 86400 AS start_day,
           CAST(strftime('%s', '2020-09-22') AS INTEGER) / 86400 AS last_day
),
dau AS (
    SELECT l.auth_ts / 86400 AS day, COUNT(DISTINCT l.uid) AS dau
    FROM logins l, params p
    WHERE l.auth_ts / 86400 BETWEEN p.start_day AND p.last_day
    GROUP BY 1
),
installs AS (
    SELECT reg_ts / 86400 AS day, COUNT(*) AS new_players
    FROM registrations GROUP BY 1
)
SELECT date(d.day * 86400, 'unixepoch') AS date, d.dau, COALESCE(i.new_players, 0) AS new_players
FROM dau d LEFT JOIN installs i USING (day)
ORDER BY d.day;
