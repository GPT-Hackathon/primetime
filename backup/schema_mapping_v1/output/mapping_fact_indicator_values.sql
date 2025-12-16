-- Schema Mapping: ccibt-hack25ww7-750.worldbank_staging_dataset.staging_life_expectancy → ccibt-hack25ww7-750.worldbank_target_dataset.fact_indicator_values
-- Generated: 2025-12-16 13:34:34
-- Total mappings: 3

INSERT INTO `ccibt-hack25ww7-750.worldbank_target_dataset.fact_indicator_values` (
  `year`,
  `indicator_code`,
  `country_key`
)

SELECT
  `year` AS `year`,   DIRECT
  `indicator_code` AS `indicator_code`,   DIRECT
  `country_code` AS `country_key`  -- DIRECT

FROM `ccibt-hack25ww7-750.worldbank_staging_dataset.staging_life_expectancy`;

-- MAPPING NOTES:
-- 
-- ⚠️ Unmapped Target Columns (not populated by this query):
--   - country_key
--   - numeric_value
--   - data_source
--   - loaded_at
-- 
-- ℹ️ Unmapped Source Columns (not used in target):
--   - country_code (STRING)
--   - iso3 (STRING)
--   - value (FLOAT)