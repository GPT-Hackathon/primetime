# Schema Mapping Report

**Source Table:** `ccibt-hack25ww7-750.worldbank_staging_dataset.staging_life_expectancy`
**Target Table:** `ccibt-hack25ww7-750.worldbank_target_dataset.fact_indicator_values`
**Generated:** 2025-12-16 13:34:34

## Mapping Summary

- ✅ **Mapped:** 3/6 columns (50.0%)
- 🎯 **High Confidence:** 3 mappings
- ⚠️ **Medium Confidence:** 0 mappings
- ❗ **Low Confidence:** 0 mappings
- 🔍 **Unmapped Target Columns:** 4
- ℹ️ **Unused Source Columns:** 3

## Column Mappings

| Source Column | Source Type | → | Target Column | Target Type | Transformation | Confidence |
|---------------|-------------|---|---------------|-------------|----------------|------------|
| `year` | INTEGER | → | `year` | INTEGER | DIRECT | 🟢 High (100%) |
| `indicator_code` | STRING | → | `indicator_code` | STRING | DIRECT | 🟢 High (100%) |
| `country_code` | STRING | → | `country_key` | STRING | DIRECT | 🟢 High (100%) |

## Mapping Details

### 1. `year` → `year`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``year``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 2. `indicator_code` → `indicator_code`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``indicator_code``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 3. `country_code` → `country_key`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``country_code``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

## ⚠️ Unmapped Target Columns

The following target columns were not mapped from the source:

- `country_key` - No matching source column found
- `numeric_value` - No matching source column found
- `data_source` - No matching source column found
- `loaded_at` - No matching source column found

> **Action Required:** These columns will be NULL unless you manually add mappings or provide default values.

## ℹ️ Unused Source Columns

The following source columns are not mapped to any target column:

- `country_code` (STRING) (closest match: `country_key` at 76%)
- `iso3` (STRING) (closest match: `data_source` at 29%)
- `value` (FLOAT) (closest match: `numeric_value` at 59%)

## 💡 Recommendations

2. **Handle Unmapped Target Columns:** Decide whether to use NULL values, default values, or add explicit mappings.
4. **Test with Sample Data:** Run the generated SQL on a small data sample before full migration.
5. **Validate Data Quality:** Check for NULL values, data truncation, and conversion errors.

## 📋 Next Steps

1. Review this mapping report thoroughly
2. Examine the generated SQL file
3. Request any changes needed via the agent
4. Once satisfied, approve the mapping
5. Test the SQL with a small data sample
6. Deploy to production ETL pipeline
