# Sample API Responses

This directory contains sample API responses from the Schema Mapping API deployed on Google Cloud Run.

## Files

### 1. sample_api_response_report.json (39KB)
**Mode:** REPORT
**Description:** Response showing unmapped columns flagged as warnings for manual review.

**Key Characteristics:**
- **Status:** success
- **Number of mappings:** 7 table mappings
- **Tables with unmapped columns:** 4
- **Unmapped columns marked as:**
  - `source_column: "UNMAPPED"`
  - `source_type: "MISSING"`
  - `transformation: null`
- **Use case:** Review what columns need manual mapping decisions

**Example unmapped column:**
```json
{
  "source_column": "UNMAPPED",
  "target_column": "loaded_at",
  "source_type": "MISSING",
  "target_type": "TIMESTAMP",
  "type_conversion_needed": false,
  "transformation": null,
  "notes": "No source column found - requires manual mapping or default value."
}
```

### 2. sample_api_response_fix.json (35KB)
**Mode:** FIX
**Description:** Response with intelligent default suggestions for unmapped columns.

**Key Characteristics:**
- **Status:** success
- **Number of mappings:** 8 table mappings
- **Total generated columns:** 39
- **Generated columns marked as:**
  - `source_column: "GENERATED"`
  - `source_type: "EXPRESSION"`
  - `transformation: "DEFAULT: <expression>"`
- **Use case:** Get automatic suggestions for default values

**Example generated columns:**
```json
{
  "source_column": "GENERATED",
  "target_column": "loaded_at",
  "source_type": "EXPRESSION",
  "target_type": "TIMESTAMP",
  "type_conversion_needed": false,
  "transformation": "DEFAULT: CURRENT_TIMESTAMP()",
  "notes": "Auto-generated timestamp for audit purposes"
}
```

```json
{
  "source_column": "GENERATED",
  "target_column": "data_source",
  "source_type": "EXPRESSION",
  "target_type": "STRING",
  "type_conversion_needed": false,
  "transformation": "DEFAULT: 'staging_gdp'",
  "notes": "Indicates the source staging table name"
}
```

```json
{
  "source_column": "GENERATED",
  "target_column": "year_key",
  "source_type": "EXPRESSION",
  "target_type": "STRING",
  "type_conversion_needed": true,
  "transformation": "DEFAULT: CAST(year AS STRING)",
  "notes": "Derived key from year column"
}
```

## API Request Used

Both samples were generated using:

```bash
curl -X POST https://schema-mapping-api-313669899210.us-central1.run.app/generate-mapping \
  -H 'Content-Type: application/json' \
  -d '{
    "source_dataset": "worldbank_staging_dataset",
    "target_dataset": "worldbank_target_dataset",
    "mode": "REPORT",  # or "FIX"
    "project_id": "ccibt-hack25ww7-750"
  }'
```

## Response Structure

Both responses follow this structure:

```json
{
  "status": "success",
  "message": null,
  "mapping": {
    "metadata": {
      "source_dataset": "...",
      "target_dataset": "...",
      "generated_at": "...",
      "confidence": "high",
      "mode": "REPORT|FIX"
    },
    "mappings": [
      {
        "source_table": "...",
        "target_table": "...",
        "match_confidence": 0.95,
        "column_mappings": [...],
        "unmapped_source_columns": [...],
        "unmapped_target_columns": [...],
        "mapping_errors": [...],
        "validation_rules": [...],
        "primary_key": [...],
        "uniqueness_constraints": [...]
      }
    ]
  },
  "metadata": {
    "source_dataset": "...",
    "target_dataset": "...",
    "mode": "...",
    "num_mappings": 7,
    "confidence": "high"
  }
}
```

## Key Differences: REPORT vs FIX Mode

| Aspect | REPORT Mode | FIX Mode |
|--------|-------------|----------|
| **Unmapped columns** | Flagged as errors | Suggestions provided |
| **source_column** | `"UNMAPPED"` | `"GENERATED"` |
| **source_type** | `"MISSING"` | `"EXPRESSION"` |
| **transformation** | `null` | `"DEFAULT: <expression>"` |
| **mapping_errors** | Contains warnings | Empty or minimal |
| **Use case** | Manual review | Automated defaults |

## Generated Default Types in FIX Mode

The API intelligently suggests defaults based on column type and name:

- **Timestamps:** `DEFAULT: CURRENT_TIMESTAMP()`
- **Data source tracking:** `DEFAULT: 'table_name'`
- **Calculated fields:** `DEFAULT: CAST(year AS STRING)`, `DEFAULT: SAFE_DIVIDE(gdp, population)`
- **Numeric defaults:** `DEFAULT: 0`
- **String defaults:** `DEFAULT: 'UNKNOWN'`
- **IDs:** `DEFAULT: UUID()` or `DEFAULT: 0`

## Notes

- All DEFAULT transformations include the **"DEFAULT:"** prefix to clearly indicate they are generated values, not from source data
- The LLM (Gemini 2.5 Flash) analyzes table/column names, types, and relationships to suggest appropriate defaults
- REPORT mode is useful for understanding data quality and mapping gaps
- FIX mode is useful for rapid prototyping and getting initial transformation suggestions

## Generated

- Date: 2025-12-16
- API Version: 1.0.0
- Service URL: https://schema-mapping-api-313669899210.us-central1.run.app
