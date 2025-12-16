# Running Schema Mapper Locally

## What This Script Does

The **Schema Mapper** is an AI-powered tool that automatically maps columns between BigQuery datasets using Gemini 1.5 Pro. It's designed for ETL/data migration scenarios.

### Features:
- 🔍 Fetches schemas from BigQuery (source and target datasets)
- 🤖 Uses Gemini 1.5 Pro to intelligently map columns
- 📊 Generates validation rules and type conversion requirements
- 🎯 Two modes: REPORT (flag issues) or FIX (suggest defaults)
- 📄 Outputs comprehensive JSON mapping file

---

## Prerequisites

### 1. Google Cloud Setup
You need:
- A GCP project with BigQuery enabled
- Source and target datasets in BigQuery
- Vertex AI API enabled
- Application Default Credentials configured

### 2. Environment Variables
Create a `.env` file in the project root or `agents/schema_mapping/` directory:

```bash
GCP_PROJECT_ID=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_CLOUD_PROJECT=your-project-id  # Same as GCP_PROJECT_ID
```

### 3. Authenticate with Google Cloud
```bash
gcloud auth application-default login
```

---

## Installation

### Option 1: Using the project's uv environment (Recommended)
```bash
# From project root
cd /Users/nkaravadi/Dev/GPTHackathon/primetime
uv sync
```

### Option 2: Manual installation
```bash
pip install google-cloud-bigquery vertexai python-dotenv
```

---

## How to Run

### Method 1: Run the Script Directly (Easiest)

```bash
# From the project root
cd /Users/nkaravadi/Dev/GPTHackathon/primetime

# Run with default datasets (worldbank example)
python agents/schema_mapping/schema_mapper.py
```

This will:
1. Fetch schemas from `worldbank_staging_dataset` and `worldbank_target_dataset`
2. Generate mapping using Gemini 1.5 Pro
3. Save output to `agents/schema_mapping/worldbank_schema_mapping.json`

### Method 2: Modify for Your Datasets

Edit the `if __name__ == "__main__":` section at the bottom of `schema_mapper.py`:

```python
if __name__ == "__main__":
    result = generate_schema_mapping(
        source_dataset="your_source_dataset",      # Change this
        target_dataset="your_target_dataset",      # Change this
        output_file="my_custom_mapping.json",      # Change this
        mode="REPORT"  # or "FIX"
    )
```

### Method 3: Use as a Module

```python
from agents.schema_mapping.schema_mapper import generate_schema_mapping

result = generate_schema_mapping(
    source_dataset="my_staging_dataset",
    target_dataset="my_prod_dataset",
    output_file="my_mapping.json",
    mode="FIX"  # Use FIX mode to get default value suggestions
)

if result["status"] == "success":
    print(f"Mapping saved to: {result['output_file']}")
    print(f"Mappings generated: {len(result['mapping']['mappings'])}")
```

---

## Modes Explained

### REPORT Mode (Default)
- Flags unmapped target columns as errors
- Sets unmapped columns to `"UNMAPPED"` with `"MISSING"` type
- Good for: Initial analysis, finding gaps

**Example:**
```json
{
  "source_column": "UNMAPPED",
  "target_column": "created_at",
  "source_type": "MISSING",
  "transformation": null,
  "notes": "No source column found - requires manual mapping or default value"
}
```

### FIX Mode
- Suggests intelligent default values for unmapped columns
- Provides transformation expressions (e.g., `"DEFAULT: CURRENT_TIMESTAMP()"`)
- Good for: Automated migration, generating executable SQL

**Example:**
```json
{
  "source_column": "GENERATED",
  "target_column": "created_at",
  "source_type": "EXPRESSION",
  "transformation": "DEFAULT: CURRENT_TIMESTAMP()",
  "notes": "Auto-generated timestamp for audit purposes"
}
```

---

## Output Format

The script generates a JSON file with this structure:

```json
{
  "metadata": {
    "source_dataset": "project.source_dataset",
    "target_dataset": "project.target_dataset",
    "generated_at": "2025-12-16T...",
    "confidence": "high",
    "mode": "REPORT"
  },
  "mappings": [
    {
      "source_table": "staging_table",
      "target_table": "dim_table",
      "match_confidence": 0.95,
      "column_mappings": [...],
      "unmapped_source_columns": [...],
      "unmapped_target_columns": [...],
      "mapping_errors": [...],
      "validation_rules": [...],
      "primary_key": ["id"],
      "uniqueness_constraints": ["id"]
    }
  ]
}
```

---

## Example Run

```bash
$ python agents/schema_mapping/schema_mapper.py

============================================================
SCHEMA MAPPING AGENT
============================================================
Source Dataset: worldbank_staging_dataset
Target Dataset: worldbank_target_dataset
Output File: worldbank_schema_mapping.json
Mode: REPORT
Model: Gemini 1.5 Pro
============================================================

Step 1: Fetching source dataset schemas...
✓ Found 8 source tables

Step 2: Fetching target dataset schemas...
✓ Found 5 target tables

Step 3: Generating schema mapping with Gemini...

Calling Gemini 1.5 Pro to generate schema mapping...
✓ LLM generated valid mapping JSON

============================================================
✓ Schema mapping saved to: worldbank_schema_mapping.json
============================================================

Summary:
  - Tables mapped: 5
  - source_gdp → target_fact_indicator_values
    Columns: 15, Rules: 8
  - source_population → target_fact_indicator_values
    Columns: 15, Rules: 8
  ...

✅ Schema mapping completed successfully!
```

---

## Troubleshooting

### Error: "Table not found"
- Verify your datasets exist: `bq ls your_dataset`
- Check your GCP_PROJECT_ID is correct
- Ensure you have BigQuery permissions

### Error: "Authentication failed"
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### Error: "Vertex AI API not enabled"
```bash
gcloud services enable aiplatform.googleapis.com
```

### Error: "Invalid model name"
- Make sure the script uses `gemini-1.5-pro` (already fixed)
- Available models: `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash-exp`

---

## Tips for Best Results

1. **Use descriptive column names** - The AI maps better with clear naming
2. **Add column descriptions** in BigQuery - Gemini uses these for context
3. **Start with REPORT mode** - Understand the gaps first
4. **Review generated mappings** - AI is smart but not perfect for complex business logic
5. **Try both modes** - Compare REPORT vs FIX to see what works best

---

## Next Steps

After generating the mapping:

1. **Review the JSON file** - Check column mappings make sense
2. **Validate transformations** - Especially DEFAULT expressions in FIX mode
3. **Test on sample data** - Use the mapping to build SQL scripts
4. **Iterate** - Refine and re-run if needed

For more details, see the main project documentation.

