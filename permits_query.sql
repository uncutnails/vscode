--tell PostgreSQL to expect Month/Day/Year format for this session
SET datestyle = 'ISO, MDY';
with get_median AS (
	select percentile_cont(0.5) within group (order by NULLIF(TRIM("Construction Value"::text), '')::numeric) as construction_median_value -- percentile functions require ordered data so witihn gorup & order by goes together
	from kw_building_permits
),
median_construction_calc as ( --subquery
	select *, (select construction_median_value from get_median) as construction_median_value
	from kw_building_permits
)
select *,
	EXTRACT(month from "Application Date"::date) as "Application_Month",
	COALESCE("Work Type", 'Unknown') as "Clean_Work_Type",
	COALESCE("Final Date"::text, 'Unfinished') as "Clean_Final_Date",
	COALESCE("Construction Value", construction_median_value) as "Clean_Construction_Value"
from median_construction_calc 
where (NULLIF(TRIM("Application Date"), '') IS NOT NULL)
    AND (NULLIF(TRIM("Issue Date"), '') IS NOT NULL)
    AND (NULLIF(TRIM("Issued By"), '') IS NOT NULL)


