-- Churn within a segment: among Cookie Cats players who came back on day 1,
-- who was gone by day 7, by how many rounds they played in their first 14 days?
SELECT
    CASE WHEN sum_gamerounds < 10 THEN '1) under 10'
         WHEN sum_gamerounds < 30 THEN '2) 10-29'
         WHEN sum_gamerounds < 100 THEN '3) 30-99'
         ELSE '4) 100+' END                      AS rounds_bucket,
    COUNT(*)                                     AS day1_returners,
    ROUND(1 - AVG(retention_7), 6)               AS churned_by_day7
FROM cookie_cats
WHERE retention_1 = 1
GROUP BY 1
ORDER BY 1;
