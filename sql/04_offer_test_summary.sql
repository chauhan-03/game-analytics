-- Offer-set A/B test: conversion, ARPU and ARPPU per group.
SELECT
    testgroup,
    COUNT(*)                                       AS players,
    SUM(revenue > 0)                               AS payers,
    ROUND(1.0 * SUM(revenue > 0) / COUNT(*), 6)    AS conversion,
    SUM(revenue)                                   AS revenue,
    ROUND(1.0 * SUM(revenue) / COUNT(*), 6)        AS arpu,
    ROUND(1.0 * SUM(revenue) / SUM(revenue > 0), 6) AS arppu,
    SUM(revenue >= 10000)                          AS payers_10k_plus,
    ROUND(1.0 * SUM(CASE WHEN revenue >= 10000 THEN revenue ELSE 0 END) / SUM(revenue), 6) AS revenue_share_10k_plus
FROM ab_test
GROUP BY testgroup
ORDER BY testgroup;
