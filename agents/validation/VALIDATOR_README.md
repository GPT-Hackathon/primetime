# Data Validation Agent

LLM-powered data validation agent that validates BigQuery staging data based on schema mapping rules.

## Overview

The Data Validation Agent takes schema mapping JSON (from the Schema Mapping Agent) and automatically:
1. Generates SQL validation queries using Gemini 2.5 Flash
2. Executes queries to find data quality issues
3. Logs errors to a `staging_errors` table in BigQuery

## Features

- ✅ **LLM-Generated SQL Queries**: Uses Gemini to create validation queries from mapping rules
- ✅ **Multiple Validation Types**:
  - UNIQUENESS: Duplicate primary key detection
  - NOT_NULL: Missing required values
  - TYPE_CONVERSION: Invalid type conversions
  - RANGE: Values outside expected ranges
  - NUMERIC: Non-numeric values in numeric columns
- ✅ **Error Tracking**: All errors logged to BigQuery with run_id, source/target tables, error messages
- ✅ **Batch Validation**: Validates all table mappings in one run

## Architecture

```
Schema Mapping JSON
        ↓
   [LLM Analysis]
   Gemini 2.5 Flash
        ↓
  SQL Validation Queries
        ↓
   [BigQuery Execution]
        ↓
  staging_errors table
```

## Input

### 1. Schema Mapping JSON

The validator accepts JSON from the Schema Mapping Agent in either format:

**API Response Format:**
```json
{
  "status": "success",
  "mapping": {
    "mappings": [...]
  }
}
```

**Direct Mapping Format:**
```json
{
  "mappings": [...]
}
```

### 2. Source Dataset Name

Example: `"worldbank_staging_dataset"`

### 3. Mode

- **REPORT**: Find and log errors (default)
- **FIX**: Auto-correct errors (not yet implemented)

## Output

### staging_errors Table Schema

```sql
CREATE TABLE `project.dataset.staging_errors` (
  run_id STRING NOT NULL,              -- GUID for this validation run
  source_table STRING NOT NULL,        -- Source table name
  target_table STRING NOT NULL,        -- Target table name
  error_message STRING NOT NULL,       -- Human-readable error description
  error_type STRING NOT NULL,          -- UNIQUENESS, NOT_NULL, TYPE_CONVERSION, RANGE, NUMERIC
  failed_column STRING,                -- Column(s) that failed validation
  row_count INTEGER NOT NULL,          -- Number of rows with this error
  created_at TIMESTAMP NOT NULL        -- When error was logged
)
```

## Usage

### Command Line

```bash
cd agents/validation

# Using schema mapping file
python data_validator.py \
  ../schema_mapping/sample_api_response_fix.json \
  worldbank_staging_dataset \
  REPORT

# Using API response
python data_validator.py \
  ../schema_mapping/worldbank_mapping_fix.json \
  worldbank_staging_dataset \
  REPORT
```

### Python Script

```python
from agents.validation.data_validator import validate_schema_mapping
import vertexai

# Initialize Vertex AI
vertexai.init(project="your-project-id", location="us-central1")

# Run validation
result = validate_schema_mapping(
    schema_mapping_json="path/to/mapping.json",
    source_dataset="worldbank_staging_dataset",
    mode="REPORT"
)

print(f"Run ID: {result['run_id']}")
print(f"Total Errors: {result['total_errors']}")
```

### Quick Test

```bash
# Use the provided test script
python run_data_validator.py
```

## Validation Types

### 1. UNIQUENESS Checks

Finds duplicate rows based on primary keys or unique constraints.

**Generated SQL Example:**
```sql
SELECT COUNT(*) as error_count
FROM (
  SELECT country_code, year, COUNT(*) as cnt
  FROM `project.worldbank_staging_dataset.staging_gdp`
  GROUP BY country_code, year
  HAVING COUNT(*) > 1
)
```

**Error Message:** "Duplicate rows found for primary key (country_code, year)"

### 2. NOT_NULL Checks

Validates required columns have no NULL values.

**Generated SQL Example:**
```sql
SELECT COUNT(*) as error_count
FROM `project.worldbank_staging_dataset.staging_gdp`
WHERE country_code IS NULL
```

**Error Message:** "NULL values found in required column country_code"

### 3. TYPE_CONVERSION Checks

Validates data can be converted to target data types.

**Generated SQL Example:**
```sql
SELECT COUNT(*) as error_count
FROM `project.worldbank_staging_dataset.staging_gdp`
WHERE value IS NOT NULL
  AND SAFE_CAST(value AS INT64) IS NULL
```

**Error Message:** "Cannot convert value to INT64 type"

### 4. RANGE Checks

Validates numeric values are within acceptable ranges.

**Generated SQL Example:**
```sql
SELECT COUNT(*) as error_count
FROM `project.worldbank_staging_dataset.staging_gdp`
WHERE year IS NOT NULL
  AND (year < 1900 OR year > 2100)
```

**Error Message:** "Year values outside valid range (1900-2100)"

### 5. NUMERIC Checks

Ensures numeric columns contain valid numbers.

**Generated SQL Example:**
```sql
SELECT COUNT(*) as error_count
FROM `project.worldbank_staging_dataset.staging_gdp`
WHERE gdp IS NOT NULL
  AND SAFE_CAST(gdp AS FLOAT64) IS NULL
```

**Error Message:** "Non-numeric values found in numeric column gdp"

## Example Workflow

### Step 1: Generate Schema Mapping

```bash
cd agents/schema_mapping
python run_schema_mapper.py
# Output: worldbank_mapping_fix.json
```

### Step 2: Run Validation

```bash
cd agents/validation
python data_validator.py \
  ../schema_mapping/worldbank_mapping_fix.json \
  worldbank_staging_dataset \
  REPORT
```

**Output:**
```
============================================================
DATA VALIDATION AGENT
============================================================
Source Dataset: worldbank_staging_dataset
Mode: REPORT
Model: Gemini 2.5 Flash
============================================================

Loaded 8 table mapping(s)

Creating/verifying staging_errors table in worldbank_staging_dataset...
✓ Ensured staging_errors table exists

Validation Run ID: 550e8400-e29b-41d4-a716-446655440000

[1/8] Processing table mapping...

============================================================
Validating: staging_gdp → fact_indicator_values
============================================================
Column mappings: 6
Validation rules: 3
Primary key: ['country_code', 'year', 'indicator_code']

🤖 Generating validation queries with Gemini...
✓ Generated 4 validation queries

[1/4] Running UNIQUENESS check...
  ✗ UNIQUENESS: 15 row(s) - Duplicate rows for primary key
[2/4] Running NOT_NULL check...
  ✓ NOT_NULL: No issues found
[3/4] Running TYPE_CONVERSION check...
  ✗ TYPE_CONVERSION: 3 row(s) - Cannot convert value to NUMERIC
[4/4] Running RANGE check...
  ✗ RANGE: 2 row(s) - Year values outside valid range

...

============================================================
VALIDATION SUMMARY
============================================================
Run ID: 550e8400-e29b-41d4-a716-446655440000
Tables Validated: 8
Total Validations Run: 32
Total Errors Found: 127

Errors logged to: ccibt-hack25ww7-750.worldbank_staging_dataset.staging_errors
Filter by run_id: 550e8400-e29b-41d4-a716-446655440000
============================================================
```

### Step 3: Query Errors

```sql
-- View all errors from this run
SELECT
  source_table,
  target_table,
  error_type,
  failed_column,
  row_count,
  error_message
FROM `ccibt-hack25ww7-750.worldbank_staging_dataset.staging_errors`
WHERE run_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY row_count DESC

-- Summary by error type
SELECT
  error_type,
  COUNT(*) as error_occurrences,
  SUM(row_count) as total_rows_affected
FROM `ccibt-hack25ww7-750.worldbank_staging_dataset.staging_errors`
WHERE run_id = '550e8400-e29b-41d4-a716-446655440000'
GROUP BY error_type
ORDER BY total_rows_affected DESC
```

## Environment Variables

```bash
# Required
export GCP_PROJECT_ID="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Optional
export GOOGLE_GENAI_USE_VERTEXAI=1
```

## Files

- `data_validator.py` - Main validation agent code
- `run_data_validator.py` - Test/demo script
- `validation_agent.py` - Old validation agent (deprecated)
- `VALIDATOR_README.md` - This file

## Integration with Schema Mapping Agent

The validator is designed to work seamlessly with the Schema Mapping Agent:

1. **Schema Mapping Agent** generates mapping JSON with validation rules
2. **Data Validation Agent** reads the JSON and validates staging data
3. Errors are logged to BigQuery for review
4. Can be used in CI/CD pipelines for automated data quality checks

## Advantages of LLM-Generated Queries

- ✅ **Intelligent**: Understands complex validation scenarios
- ✅ **Flexible**: Adapts to different table structures and rules
- ✅ **Maintainable**: No hardcoded SQL templates
- ✅ **Comprehensive**: Generates multiple checks per rule type
- ✅ **Contextual**: Considers relationships between columns and tables

## Error Handling

- SQL syntax errors are caught and logged
- Failed queries don't stop validation of other tables
- All errors include source table, target table, and error context
- Run ID allows filtering/grouping errors from specific validation runs

## Future Enhancements

- [ ] FIX mode implementation (auto-correct errors)
- [ ] Custom validation rule support
- [ ] Email/Slack notifications for critical errors
- [ ] Validation reports in HTML/PDF format
- [ ] Historical trend analysis
- [ ] Integration with data lineage tools

## Version

**Version:** 1.0.0
**Last Updated:** 2025-12-16
**Model:** Gemini 2.5 Flash
