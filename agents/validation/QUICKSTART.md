# Quick Start Guide - Validation Agent

## Prerequisites

1. **Google Cloud Project** with BigQuery enabled
2. **Service Account** with BigQuery permissions:
   - BigQuery Data Editor
   - BigQuery Job User
3. **Python 3.11+** installed
4. **World Bank Dataset** in `dataSets/Sample-DataSet-WorldBankData/SourceSchemaData/`

## Setup (5 minutes)

### 1. Configure GCP Credentials

```bash
# Create a service account key in GCP Console
# Download the JSON key file

# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

Or create a `.env` file:
```bash
cd agents/validation
cp .env.example .env
# Edit .env with your values
```

### 2. Install Dependencies

```bash
# From project root
pip install -r requirements.txt
# Or if using pyproject.toml
pip install -e .
```

### 3. Verify Dataset

```bash
# Check that source files exist
ls -la dataSets/Sample-DataSet-WorldBankData/SourceSchemaData/

# Should see:
# source_countries.csv
# source_gdp.csv
# source_population.csv
# ... and 5 more CSV files
```

## Usage

### Run Validation in REPORT Mode

Find and report all data quality issues:

```bash
python agents/validation/main.py --mode REPORT
```

**What it does:**
1. Loads all CSV files into BigQuery `staging.*` tables
2. Runs validation rules against each table
3. Logs errors to `staging.staging_errors` table
4. Prints summary of issues found

**Example Output:**
```
============================================================
VALIDATION AGENT
============================================================
Project ID: your-project-id
Mode: REPORT
============================================================

============================================================
Step 1: Loading Staging Data
============================================================
Loading schema from .../mock_schema.json
BigQuery Client initialized.
Loading .../source_countries.csv into your-project-id.staging.countries...
Loaded 50 rows and 5 columns to your-project-id.staging.countries
...

✓ Staging data loaded successfully

============================================================
Step 3: Running Validation Agent (Mode: REPORT)
============================================================
✓ Vertex AI initialized (Project: your-project-id, Location: us-central1)

[1/8] Validating: staging.countries
    Rules: 2 validation rule(s)
    ✓ Found 0 error(s)

[2/8] Validating: staging.gdp
    Rules: 2 validation rule(s)
    ✓ Found 3 error(s)
...

============================================================
Validation Summary
============================================================
Tables Processed: 8/8
Total Errors Found: 15

Check staging.staging_errors table for error details.
============================================================
```

### Run Validation in FIX Mode

Automatically correct data quality issues:

```bash
python agents/validation/main.py --mode FIX
```

**What it does:**
1. Loads all CSV files into BigQuery `staging.*` tables
2. Runs validation rules
3. **Auto-fixes** correctable errors:
   - NULL values in required fields → Set to defaults
   - Invalid numeric values → Set to NULL
   - Range violations → **NOT fixed** (logged only)
4. Prints summary of corrections made

**Safety Note:** Range violations are NOT auto-fixed to prevent data corruption. These require manual review.

### Skip Data Loading (Use Existing Tables)

If tables are already loaded:

```bash
python agents/validation/main.py --mode REPORT --skip-load
```

## View Results

### Query Error Table

```sql
-- View all errors
SELECT *
FROM `your-project-id.staging.staging_errors`
ORDER BY timestamp DESC
LIMIT 100;

-- Count errors by table
SELECT source_table, COUNT(*) as error_count
FROM `your-project-id.staging.staging_errors`
GROUP BY source_table
ORDER BY error_count DESC;

-- View specific violation types
SELECT violation_type, COUNT(*) as count
FROM `your-project-id.staging.staging_errors`
GROUP BY violation_type;
```

### Query Staging Tables

```sql
-- Check countries table
SELECT * FROM `your-project-id.staging.countries` LIMIT 10;

-- Check for NULL values
SELECT * FROM `your-project-id.staging.gdp`
WHERE country_code IS NULL OR year IS NULL;

-- Check range violations
SELECT * FROM `your-project-id.staging.life_expectancy`
WHERE value < 0 OR value > 120;
```

## Troubleshooting

### Error: "BigQuery Client Init Failed"

**Cause:** Invalid credentials or permissions

**Fix:**
```bash
# Verify credentials file exists
ls -la $GOOGLE_APPLICATION_CREDENTIALS

# Test authentication
gcloud auth application-default print-access-token

# Grant required permissions in GCP Console:
# - BigQuery Data Editor
# - BigQuery Job User
```

### Error: "Schema file not found"

**Cause:** Running from wrong directory

**Fix:**
```bash
# Must run from project root
cd /path/to/primetime
python agents/validation/main.py --mode REPORT
```

### Error: "Source file not found"

**Cause:** Dataset files missing

**Fix:**
```bash
# Verify dataset exists
ls dataSets/Sample-DataSet-WorldBankData/SourceSchemaData/

# If missing, check that dataset was properly cloned/downloaded
```

### Error: "Vertex AI initialization failed"

**Cause:** Vertex AI API not enabled or wrong location

**Fix:**
```bash
# Enable Vertex AI API in GCP Console
gcloud services enable aiplatform.googleapis.com

# Or set correct region
export GOOGLE_CLOUD_LOCATION="us-central1"
```

## Next Steps

1. **Review Errors:** Query `staging.staging_errors` to see what issues were found
2. **Customize Rules:** Edit `mock/mock_schema.json` to add/modify validation rules
3. **Add Tables:** Add new source files and schema mappings
4. **Integrate:** Use validation results in your data pipeline

## Advanced Usage

### Load Data Only

```bash
python agents/validation/infrastructure/load_staging.py
```

### Run Unit Tests

```bash
cd agents/validation/tests
python -m unittest test_validation_agent.py
```

### Custom Validation Rules

Edit `agents/validation/mock/mock_schema.json`:

```json
{
  "source_file": "your_file.csv",
  "target_table": "staging.your_table",
  "schema": [...],
  "rules": [
    {"column": "id", "type": "NOT_NULL"},
    {"column": "amount", "type": "RANGE", "min": 0, "max": 1000000},
    {"column": "price", "type": "NUMERIC"}
  ]
}
```

## Support

- See full documentation: [README.md](README.md)
- Report issues: Check your GCP project logs in Cloud Console
- Debugging: Set `verbose=True` in main.py line 65
