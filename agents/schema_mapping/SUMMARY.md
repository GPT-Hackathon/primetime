# Schema Mapping Agent - Summary

## What It Does

The Schema Mapping Agent uses Gemini 2.5 Flash LLM to automatically generate intelligent mappings between BigQuery staging and target datasets, including:

- Table matching (staging → target)
- Column mappings with type conversions
- Validation rules (NOT_NULL, NUMERIC, RANGE, FOREIGN_KEY, UNIQUENESS)
- Primary keys and uniqueness constraints
- Unmapped column handling (REPORT or FIX modes)

## Key Features

### ✅ Automated Schema Analysis
- Fetches table schemas from BigQuery datasets
- Uses LLM to intelligently match tables and columns
- Considers naming similarity, data types, and business meaning

### ✅ Two Modes: REPORT vs FIX

**REPORT Mode** (Default):
- Flags unmapped target columns as `"UNMAPPED"`
- Marks source type as `"MISSING"`
- Creates `mapping_errors` array for UI display
- Use this to review what needs manual intervention

**FIX Mode**:
- Suggests intelligent defaults for unmapped columns
- Uses `"GENERATED"` for source_column
- Uses `"EXPRESSION"` for source_type
- Provides SQL transformations with **DEFAULT:** prefix:
  - Timestamp columns → `"DEFAULT: CURRENT_TIMESTAMP()"`
  - Data source columns → `"DEFAULT: 'table_name'"`
  - Calculated fields → `"DEFAULT: gdp / population"`
  - Numeric defaults → `"DEFAULT: 0"`
  - String defaults → `"DEFAULT: 'UNKNOWN'"`
- **Why DEFAULT prefix?** Makes it clear these are generated values, not from source data
- Use this for automatic default value suggestions

### ✅ Smart Validation Rules
- NOT_NULL for REQUIRED columns
- NUMERIC checks for numeric types
- RANGE validation (year: 1900-2100, percentage: 0-100, etc.)
- FOREIGN_KEY constraints
- UNIQUENESS for primary keys

## Usage

### Basic Usage

```bash
# REPORT mode - flag unmapped columns
python agents/schema_mapping/run_schema_mapper.py \
    --source worldbank_staging_dataset \
    --target worldbank_target_dataset \
    --output mapping.json \
    --mode REPORT

# FIX mode - suggest defaults
python agents/schema_mapping/run_schema_mapper.py \
    --source worldbank_staging_dataset \
    --target worldbank_target_dataset \
    --output mapping.json \
    --mode FIX
```

### Command Line Options

```
--source    Source BigQuery dataset (required)
--target    Target BigQuery dataset (required)
--output    Output JSON filename (default: schema_mapping_output.json)
--mode      REPORT or FIX (default: REPORT)
```

## Output Format

### REPORT Mode Output

```json
{
  "metadata": {
    "source_dataset": "project.staging",
    "target_dataset": "project.target",
    "mode": "REPORT",
    "confidence": "high"
  },
  "mappings": [
    {
      "source_table": "staging.countries",
      "target_table": "target.dim_country",
      "column_mappings": [
        {
          "source_column": "UNMAPPED",
          "target_column": "audit_timestamp",
          "source_type": "MISSING",
          "target_type": "TIMESTAMP",
          "transformation": null,
          "notes": "No source column found"
        }
      ],
      "mapping_errors": [
        {
          "error_type": "UNMAPPED_TARGET_COLUMN",
          "target_column": "audit_timestamp",
          "severity": "WARNING",
          "message": "Target column has no source mapping"
        }
      ]
    }
  ]
}
```

### FIX Mode Output

```json
{
  "metadata": {
    "mode": "FIX"
  },
  "mappings": [
    {
      "column_mappings": [
        {
          "source_column": "GENERATED",
          "target_column": "loaded_at",
          "source_type": "EXPRESSION",
          "target_type": "TIMESTAMP",
          "transformation": "DEFAULT: CURRENT_TIMESTAMP()",
          "notes": "Auto-generated timestamp for audit purposes"
        },
        {
          "source_column": "GENERATED",
          "target_column": "data_source",
          "source_type": "EXPRESSION",
          "target_type": "STRING",
          "transformation": "DEFAULT: 'staging_gdp'",
          "notes": "Indicates the source staging table name"
        }
      ]
    }
  ]
}
```

## Example Results

### World Bank Datasets

**Run**: FIX mode on worldbank_staging_dataset → worldbank_target_dataset

**Results**:
- **5 table mappings** generated
- **Dimensional model** correctly identified:
  - staging_countries → dim_country
  - staging_indicators_meta → dim_indicator
  - staging_gdp → dim_time
  - Multiple staging tables → fact_indicator_values
  - staging_gdp → agg_country_year

**Smart Defaults Generated** (with DEFAULT: prefix):
- `loaded_at` → `"DEFAULT: CURRENT_TIMESTAMP()"`
- `data_source` → `"DEFAULT: 'staging_table_name'"`
- `gdp_per_capita` → `"DEFAULT: gdp / population"` (calculated field)
- `year_key` → `"DEFAULT: CAST(year AS STRING)"`

**Validation Rules**:
- NOT_NULL for primary keys
- NUMERIC_RANGE for years (1900-2100)
- NUMERIC_RANGE for percentages (0-100)
- FOREIGN_KEY constraints identified

## Integration with Validation Agent

The generated mapping JSON can be used directly by the validation agent:

```python
import json
from agents.validation.validation_agent import validate_data

# Load mapping
with open("worldbank_mapping_fix.json") as f:
    mapping = json.load(f)

# Use validation rules from mapping
for table_mapping in mapping["mappings"]:
    rules = table_mapping["validation_rules"]
    target_table = table_mapping["target_table"]
    validate_data(target_table, json.dumps(rules), "REPORT")
```

## Files

- `schema_mapper.py` - Core LLM-based mapping generator
- `run_schema_mapper.py` - CLI interface
- `README.md` - Complete documentation
- `SUMMARY.md` - This file
- `__init__.py` - Package exports

## Technology Stack

- **LLM**: Gemini 2.5 Flash (via Vertex AI)
- **Schema Source**: BigQuery INFORMATION_SCHEMA
- **Output**: Structured JSON
- **Mode**: Function calling for structured output

## Comparison: REPORT vs FIX

| Aspect | REPORT Mode | FIX Mode |
|--------|-------------|----------|
| **Unmapped columns** | Flagged as errors | Defaults suggested |
| **source_column** | `"UNMAPPED"` | `"GENERATED"` |
| **source_type** | `"MISSING"` | `"EXPRESSION"` |
| **transformation** | `null` | SQL expression |
| **mapping_errors** | Populated | Empty |
| **Use case** | Review & manual fix | Auto-apply defaults |

## Success Criteria

✅ Fetches schemas from BigQuery
✅ Uses LLM for intelligent mapping
✅ Handles unmapped columns (2 modes)
✅ NEVER outputs null for source_column/source_type
✅ Generates validation rules automatically
✅ Identifies primary keys and foreign keys
✅ Outputs valid, parseable JSON
✅ CLI interface with mode selection

## Known Limitations

1. **Rate Limits**: Vertex AI may throttle requests - add retry logic if needed
2. **Schema Size**: Very large datasets (100+ tables) may hit token limits
3. **Complex Joins**: Aggregate tables requiring multi-table joins need manual review
4. **LLM Variability**: Output may vary slightly between runs

## Future Enhancements

1. Add batch processing for multiple dataset pairs
2. Generate ETL SQL from mappings
3. Add confidence thresholds for manual review
4. Support for custom mapping rules
5. UI for reviewing and editing mappings
6. Integration with data lineage tools

---

**Last Updated**: 2025-12-16
**Version**: 1.0.0
**Model**: Gemini 2.5 Flash
