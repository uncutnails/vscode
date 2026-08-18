WITH get_median AS (
    SELECT 
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY NULLIF(TRIM("CONSTRUCTION_VALUE"::text), '')::NUMERIC
        ) AS construction_median_value 
    FROM kitchener_buildings_permits
)
select p.*,
	EXTRACT(month from "APPLICATION_DATE") as "APPLICATION_MONTH",
	COALESCE(p."WORK_TYPE", 'Unknown') as "CLEAN_WORK_TYPE",
	COALESCE(p."FINAL_DATE"::text, 'Unfinished') as "CLEAN_FINAL_DATE",
	COALESCE(p."CONSTRUCTION_VALUE", construction_median_value) as "CLEAN_CONSTRUCTION_VALUE"
FROM kitchener_buildings_permits p
CROSS JOIN get_median m
where 
	"APPLICATION_DATE" IS NOT NULL
    AND "ISSUE_DATE" IS NOT NULL
    AND "ISSUED_BY" IS NOT NULL

