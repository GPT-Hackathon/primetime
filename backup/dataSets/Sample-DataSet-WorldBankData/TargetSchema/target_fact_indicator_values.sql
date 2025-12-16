CREATE TABLE `project.dataset.fact_indicator_values` (
  country_key STRING,
  year INT64,
  indicator_code STRING,
  numeric_value NUMERIC,
  data_source STRING,
  loaded_at TIMESTAMP
);
