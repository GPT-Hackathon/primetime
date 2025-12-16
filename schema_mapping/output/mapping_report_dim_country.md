# Schema Mapping Report

**Source Table:** `ccibt-hack25ww7-750.worldbank_staging_dataset.staging_countries`
**Target Table:** `ccibt-hack25ww7-750.worldbank_target_dataset.dim_country`
**Generated:** 2025-12-16 12:55:30

## Mapping Summary

- ✅ **Mapped:** 4/5 columns (80.0%)
- 🎯 **High Confidence:** 4 mappings
- ⚠️ **Medium Confidence:** 0 mappings
- ❗ **Low Confidence:** 0 mappings
- 🔍 **Unmapped Target Columns:** 1
- ℹ️ **Unused Source Columns:** 1

## Column Mappings

| Source Column | Source Type | → | Target Column | Target Type | Transformation | Confidence |
|---------------|-------------|---|---------------|-------------|----------------|------------|
| `country_name` | STRING | → | `country_name` | STRING | DIRECT | 🟢 High (100%) |
| `region` | STRING | → | `region` | STRING | DIRECT | 🟢 High (100%) |
| `income_group` | STRING | → | `income_group` | STRING | DIRECT | 🟢 High (100%) |
| `iso3` | STRING | → | `iso3` | STRING | DIRECT | 🟢 High (100%) |

## Mapping Details

### 1. `country_name` → `country_name`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``country_name``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 2. `region` → `region`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``region``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 3. `income_group` → `income_group`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``income_group``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 4. `iso3` → `iso3`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``iso3``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

## ⚠️ Unmapped Target Columns

The following target columns were not mapped from the source:

- `country_key` - No matching source column found

> **Action Required:** These columns will be NULL unless you manually add mappings or provide default values.

## ℹ️ Unused Source Columns

The following source columns are not mapped to any target column:

- `country_code` (STRING) (closest match: `country_key` at 76%)

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
