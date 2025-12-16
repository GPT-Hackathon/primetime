# Schema Mapping Report

**Source Table:** `ccibt-hack25ww7-750.worldbank_staging_dataset.staging_indicators_meta`
**Target Table:** `ccibt-hack25ww7-750.worldbank_target_dataset.dim_indicator`
**Generated:** 2025-12-16 12:41:43

## Mapping Summary

- ✅ **Mapped:** 3/3 columns (100.0%)
- 🎯 **High Confidence:** 3 mappings
- ⚠️ **Medium Confidence:** 0 mappings
- ❗ **Low Confidence:** 0 mappings

## Column Mappings

| Source Column | Source Type | → | Target Column | Target Type | Transformation | Confidence |
|---------------|-------------|---|---------------|-------------|----------------|------------|
| `indicator_code` | STRING | → | `indicator_code` | STRING | DIRECT | 🟢 High (100%) |
| `indicator_name` | STRING | → | `indicator_name` | STRING | DIRECT | 🟢 High (100%) |
| `topic` | STRING | → | `topic` | STRING | DIRECT | 🟢 High (100%) |

## Mapping Details

### 1. `indicator_code` → `indicator_code`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``indicator_code``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 2. `indicator_name` → `indicator_name`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``indicator_name``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 3. `topic` → `topic`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``topic``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

## 💡 Recommendations

4. **Test with Sample Data:** Run the generated SQL on a small data sample before full migration.
5. **Validate Data Quality:** Check for NULL values, data truncation, and conversion errors.

## 📋 Next Steps

1. Review this mapping report thoroughly
2. Examine the generated SQL file
3. Request any changes needed via the agent
4. Once satisfied, approve the mapping
5. Test the SQL with a small data sample
6. Deploy to production ETL pipeline
