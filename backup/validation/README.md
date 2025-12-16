# Validation Agent

## Overview
The Validation Agent scans actual data files for errors and either reports or fixes them according to defined validation rules.

## Architecture

### Components

1. **Infrastructure Layer** (`infrastructure/load_staging.py`)
   - Loads CSV files from `dataSets/Sample-DataSet-WorldBankData/SourceSchemaData/` into BigQuery staging tables
   - Creates tables dynamically based on schema definitions
   - Supports idempotent loading (WRITE_TRUNCATE mode)

2. **Schema Configuration** (`mock/mock_schema.json`)
   - Defines mappings between source CSV files and target BigQuery tables
   - Specifies column schemas and data types
   - Defines validation rules for each table

3. **Validation Agent** (`validation_agent.py`)
   - Core validation logic using Vertex AI Agent
   - Supports two modes: REPORT and FIX
   - Implements validation rules: NOT_NULL, NUMERIC, RANGE

4. **Main Entry Point** (`main.py`)
   - Orchestrates the complete workflow
   - Handles CLI arguments
   - Manages async execution

## Validation Rules

### Rule Types

1. **NOT_NULL**: Checks if required columns have null values
   - Example: `{"column": "country_code", "type": "NOT_NULL"}`

2. **NUMERIC**: Validates that values in numeric columns are actually numeric
   - Example: `{"column": "value", "type": "NUMERIC"}`

3. **RANGE**: Validates that values fall within specified ranges
   - Example: `{"column": "year", "type": "RANGE", "min": 1900, "max": 2100}`

## Usage

### Prerequisites
```bash
# Set required environment variables
export GCP_PROJECT_ID="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

### Running the Agent

#### REPORT Mode (Find and log errors)
```bash
python agents/validation/main.py --mode REPORT
```

This will:
1. Load all CSV files into staging tables
2. Run validation rules against each table
3. Insert error records into `staging.staging_errors` table
4. Print summary of errors found

#### FIX Mode (Auto-correct errors)
```bash
python agents/validation/main.py --mode FIX
```

This will:
1. Load all CSV files into staging tables
2. Run validation rules against each table
3. Automatically fix correctable errors:
   - NOT_NULL violations: Set to default values ('UNKNOWN' for strings, 0 for numbers)
   - NUMERIC violations: Set invalid numeric values to NULL
   - RANGE violations: Logged but NOT auto-fixed (requires manual review)
4. Print summary of corrections made

#### Skip Loading (Use existing tables)
```bash
python agents/validation/main.py --mode REPORT --skip-load
```

### Infrastructure Only (Load staging tables)
```bash
python agents/validation/infrastructure/load_staging.py
```

## Staged Tables

The following tables are created in the `staging` dataset:

- `staging.countries` - Country metadata
- `staging.indicators_meta` - Indicator definitions
- `staging.gdp` - GDP time series data
- `staging.population` - Population time series data
- `staging.life_expectancy` - Life expectancy data
- `staging.co2_emissions` - CO2 emissions data
- `staging.primary_enrollment` - Primary school enrollment data
- `staging.poverty_headcount` - Poverty statistics

## Error Table Schema

Errors are logged to `staging.staging_errors`:

```
- source_table (STRING): Full table ID where error was found
- failed_column (STRING): Column that failed validation
- violation_type (STRING): Type of rule that was violated
- row_data (STRING): JSON representation of the failed row
- timestamp (TIMESTAMP): When the error was detected
```

## Testing

Run unit tests:
```bash
python -m pytest agents/validation/tests/
```

Or using unittest:
```bash
python -m unittest agents/validation/tests/test_validation_agent.py
```

## Configuration

### Adding New Tables

To add a new source file for validation:

1. Add the CSV file to `dataSets/Sample-DataSet-WorldBankData/SourceSchemaData/`
2. Update `agents/validation/mock/mock_schema.json`:

```json
{
  "source_file": "source_your_file.csv",
  "target_table": "staging.your_table",
  "schema": [
    {"name": "column1", "type": "STRING", "mode": "REQUIRED"},
    {"name": "column2", "type": "INTEGER", "mode": "NULLABLE"}
  ],
  "rules": [
    {"column": "column1", "type": "NOT_NULL"},
    {"column": "column2", "type": "RANGE", "min": 0, "max": 100}
  ]
}
```

### Customizing Validation Rules

Edit the `rules` array in `mock_schema.json` for any table. Multiple rules can be applied to the same column.

## Design Decisions

1. **Auto-fix Safety**: RANGE violations are NOT auto-fixed in FIX mode to prevent data corruption
2. **Idempotency**: Loading uses WRITE_TRUNCATE to ensure repeatable runs
3. **Type Mapping**: NUMERIC in schema maps to FLOAT64 in BigQuery for consistency
4. **Error Handling**: All errors are logged; partial failures don't stop processing

## Limitations

- Currently only supports CSV files
- Fix mode uses simple default values (may need customization per use case)
- No support for complex validation rules (e.g., cross-column dependencies)
- No incremental loading (full table refresh each time)

## Future Enhancements

- Support for additional file formats (JSON, Parquet)
- More sophisticated fix strategies
- Validation rule templates
- Dashboard for error visualization
- Integration with data quality monitoring tools
