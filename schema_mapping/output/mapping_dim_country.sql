-- Schema Mapping: ccibt-hack25ww7-750.worldbank_staging_dataset.staging_countries → ccibt-hack25ww7-750.worldbank_target_dataset.dim_country
-- Generated: 2025-12-16 12:55:30
-- Total mappings: 4

INSERT INTO `ccibt-hack25ww7-750.worldbank_target_dataset.dim_country` (
  `country_name`,
  `region`,
  `income_group`,
  `iso3`
)

SELECT
  `country_name` AS `country_name`,   DIRECT
  `region` AS `region`,   DIRECT
  `income_group` AS `income_group`,   DIRECT
  `iso3` AS `iso3`  -- DIRECT

FROM `ccibt-hack25ww7-750.worldbank_staging_dataset.staging_countries`;

-- MAPPING NOTES:
-- 
-- ⚠️ Unmapped Target Columns (not populated by this query):
--   - country_key
-- 
-- ℹ️ Unmapped Source Columns (not used in target):
--   - country_code (STRING)