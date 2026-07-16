# Utilization Rate Computation

Compute utilization per 1000 members for emergency department visits, inpatient admissions, and 30-day readmissions.

## SQL

```sql
-- Utilization rates per 1000 members: ED, inpatient, 30-day readmissions
WITH members AS (
    SELECT COUNT(DISTINCT member_id) AS member_count FROM continuously_enrolled WHERE is_continuously_enrolled = 1
),
ed AS (
    SELECT COUNT(*) AS cnt FROM claims WHERE revenue_code IN ('0450','0451','0452','0456','0459') AND service_date BETWEEN '2025-01-01' AND '2025-12-31'
),
ip AS (
    SELECT COUNT(DISTINCT claim_id) AS cnt FROM claims WHERE claim_type = 'inpatient' AND admit_date BETWEEN '2025-01-01' AND '2025-12-31'
),
readmit AS (
    SELECT COUNT(*) AS cnt FROM (
        SELECT member_id, admit_date, LAG(discharge_date) OVER (PARTITION BY member_id ORDER BY admit_date) AS prev_dc
        FROM claims WHERE claim_type = 'inpatient' AND admit_date BETWEEN '2025-01-01' AND '2025-12-31'
    ) s WHERE DATEDIFF(day, prev_dc, admit_date) <= 30 AND prev_dc IS NOT NULL
)
SELECT ROUND(ed.cnt * 1000.0 / m.member_count, 1) AS ed_per_1000,
       ROUND(ip.cnt * 1000.0 / m.member_count, 1) AS ip_per_1000,
       ROUND(readmit.cnt * 1000.0 / m.member_count, 1) AS readmit_per_1000
FROM members m, ed, ip, readmit;
```

Inpatient metrics use `admit_date` and `discharge_date`, not `service_date`: admissions, readmissions, and length of stay are defined by admission events, not individual service lines. The readmission flag uses a 30-day window from the prior discharge.
