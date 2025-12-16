-- Schema Mapping: ccibt-hack25ww7-750.worldbank_staging_dataset.staging_indicators_meta → ccibt-hack25ww7-750.worldbank_target_dataset.dim_indicator
-- Generated: 2025-12-16 12:41:43
-- Total mappings: 3

INSERT INTO `ccibt-hack25ww7-750.worldbank_target_dataset.dim_indicator` (
  `indicator_code`,
  `indicator_name`,
  `topic`
)

SELECT
  `indicator_code` AS `indicator_code`,   DIRECT
  `indicator_name` AS `indicator_name`,   DIRECT
  `topic` AS `topic`  -- DIRECT

FROM `ccibt-hack25ww7-750.worldbank_staging_dataset.staging_indicators_meta`;

-- MAPPING NOTES: