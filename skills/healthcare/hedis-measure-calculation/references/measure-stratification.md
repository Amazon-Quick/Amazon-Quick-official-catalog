# Measure Stratification by Plan / Provider

Report a measure rate broken out by health plan and assigned primary care provider, ordered so the lowest-performing cells surface first. Assumes denominator, exclusion, and numerator member sets are already materialized.

## SQL

```sql
-- Measure rate stratified by health plan and provider
SELECT health_plan, assigned_pcp_npi,
       COUNT(*) - SUM(CASE WHEN e.member_id IS NOT NULL THEN 1 ELSE 0 END) AS eligible_denom,
       SUM(CASE WHEN e.member_id IS NULL AND n.member_id IS NOT NULL THEN 1 ELSE 0 END) AS numerator,
       ROUND(SUM(CASE WHEN e.member_id IS NULL AND n.member_id IS NOT NULL THEN 1 ELSE 0 END) * 100.0
             / NULLIF(COUNT(*) - SUM(CASE WHEN e.member_id IS NOT NULL THEN 1 ELSE 0 END), 0), 1) AS rate_pct
FROM denominator_members m
LEFT JOIN exclusion_members e ON m.member_id = e.member_id
LEFT JOIN numerator_members n ON m.member_id = n.member_id
GROUP BY health_plan, assigned_pcp_npi
ORDER BY rate_pct ASC;
```

The eligible denominator subtracts exclusions per group, and `NULLIF(..., 0)` guards against divide-by-zero when a plan/provider cell has no eligible members after exclusions.
