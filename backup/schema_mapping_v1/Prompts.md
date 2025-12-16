

What can you do?

---------------

Can you map schemas for the source: ccibt-hack25ww7-750.worldbank_staging_dataset and target: ccibt-hack25ww7-750.worldbank_target_dataset

---------------

Discover and map all matching table pairs
---------------


Here is the description of the source dataset

Source Table Descriptions

countries

File: source_countries.csv Columns:

country_code (STRING) - Internal country code
country_name (STRING) - Full country name
region (STRING) - World Bank region grouping
income_group (STRING) - World Bank income classification
iso3 (STRING) - ISO3 country code
indicators_meta

File: source_indicators_meta.csv Columns:

indicator_code (STRING) -
indicator_name (STRING) -
topic (STRING) -
gdp

File: source_gdp.csv Columns:

country_code (STRING) -
iso3 (STRING) -
year (INTEGER) -
indicator_code (STRING) -
value (NUMERIC) -
population

File: source_population.csv Columns:

country_code (STRING) -
iso3 (STRING) -
year (INTEGER) -
indicator_code (STRING) -
value (INTEGER) -
life_expectancy

File: source_life_expectancy.csv Columns:

country_code (STRING) -
iso3 (STRING) -
year (INTEGER) -
indicator_code (STRING) -
value (FLOAT) -
co2_emissions

File: source_co2_emissions.csv Columns:

country_code (STRING) -
iso3 (STRING) -
year (INTEGER) -
indicator_code (STRING) -
value (INTEGER) -
primary_enrollment

File: source_primary_enrollment.csv Columns:
country_code (STRING) -
iso3 (STRING) -
year (INTEGER) -
indicator_code (STRING) -
value (FLOAT) -
poverty_headcount

File: source_poverty_headcount.csv Columns:
country_code (STRING) -
iso3 (STRING) -
year (INTEGER) -
indicator_code (STRING) -
value (FLOAT) -
And here is the description of the target data set:
Target Table Descriptions
dim_country
DDL file: target_dim_country.sql Description: Denormalized country dimension for analytical joins.
dim_time
DDL file: target_dim_time.sql Description: Year dimension.
dim_indicator
DDL file: target_dim_indicator.sql Description: Indicator metadata.
fact_indicator_values
DDL file: target_fact_indicator_values.sql Description: Fact table storing numeric values for indicators across countries and years.
agg_country_year
DDL file: target_agg_country_year.sql Description: Pre-aggregated table for reporting: one row per country-year with commonly used metrics.

Can you map all tables from both datasets now?


---------------

1) country_key and country_code are the same for each of the source indicator tables (gdp, life_expectancy, population, poverty_headcount, primary_enrollment)

2) The numeric_value should be mapped to the value in the indicator table.

3) The data_source for the indicator table should be the table it was loaded from

4) set loaded_at to system time

----
