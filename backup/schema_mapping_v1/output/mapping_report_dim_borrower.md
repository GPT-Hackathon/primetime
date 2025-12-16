# Schema Mapping Report

**Source Table:** `ccibt-hack25ww7-750.test_dataset.borrower`
**Target Table:** `ccibt-hack25ww7-750.test_dataset.dim_borrower`
**Generated:** 2025-12-16 11:26:06

## Mapping Summary

- ✅ **Mapped:** 12/12 columns (100.0%)
- 🎯 **High Confidence:** 12 mappings
- ⚠️ **Medium Confidence:** 0 mappings
- ❗ **Low Confidence:** 0 mappings

## Column Mappings

| Source Column | Source Type | → | Target Column | Target Type | Transformation | Confidence |
|---------------|-------------|---|---------------|-------------|----------------|------------|
| `borrower_id` | INTEGER | → | `borrower_id` | INTEGER | DIRECT | 🟢 High (100%) |
| `borrower_name` | STRING | → | `borrower_name` | STRING | DIRECT | 🟢 High (100%) |
| `borrower_type` | STRING | → | `borrower_type` | STRING | DIRECT | 🟢 High (100%) |
| `industry` | STRING | → | `industry` | STRING | DIRECT | 🟢 High (100%) |
| `tax_id` | INTEGER | → | `tax_id` | STRING | CAST_TO_STRING | 🟢 High (100%) |
| `country` | STRING | → | `country` | STRING | DIRECT | 🟢 High (100%) |
| `state` | STRING | → | `state` | STRING | DIRECT | 🟢 High (100%) |
| `city` | STRING | → | `city` | STRING | DIRECT | 🟢 High (100%) |
| `postal_code` | INTEGER | → | `postal_code` | STRING | CAST_TO_STRING | 🟢 High (100%) |
| `inception_date` | DATE | → | `inception_date` | DATE | DIRECT | 🟢 High (100%) |
| `annual_revenue` | FLOAT | → | `annual_revenue` | NUMERIC | DIRECT | 🟢 High (100%) |
| `employees` | INTEGER | → | `employees` | INTEGER | DIRECT | 🟢 High (100%) |

## Mapping Details

### 1. `borrower_id` → `borrower_id`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``borrower_id``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 2. `borrower_name` → `borrower_name`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``borrower_name``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 3. `borrower_type` → `borrower_type`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``borrower_type``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 4. `industry` → `industry`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``industry``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 5. `tax_id` → `tax_id`

- **Transformation:** `CAST_TO_STRING`
- **SQL Expression:** `CAST(`tax_id` AS STRING)`
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 6. `country` → `country`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``country``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 7. `state` → `state`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``state``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 8. `city` → `city`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``city``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 9. `postal_code` → `postal_code`

- **Transformation:** `CAST_TO_STRING`
- **SQL Expression:** `CAST(`postal_code` AS STRING)`
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 10. `inception_date` → `inception_date`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``inception_date``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 11. `annual_revenue` → `annual_revenue`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``annual_revenue``
- **Type Compatibility:** ✅ Compatible
- **Confidence:** High (similarity: 100%)

### 12. `employees` → `employees`

- **Transformation:** `DIRECT`
- **SQL Expression:** ``employees``
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
