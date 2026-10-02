-- Cookie Cats gate test: D1/D7 retention and early progress by gate position.
SELECT
    version,
    COUNT(*)                                   AS players,
    ROUND(AVG(retention_1), 6)                 AS d1_retention,
    ROUND(AVG(retention_7), 6)                 AS d7_retention,
    ROUND(AVG(sum_gamerounds < 10), 6)         AS under_10_rounds,
    ROUND(AVG(sum_gamerounds >= 30), 6)        AS reached_30_rounds
FROM cookie_cats
GROUP BY version
ORDER BY version;
