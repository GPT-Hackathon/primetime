# Flexible Schema Detection

The staging_loader_agent now supports **flexible schema file detection** - it will find and use any schema file with "schema" in its name!

## ✅ Supported Schema File Names

The agent will automatically find any of these (and more):

```
✅ schema.json
✅ source_schema.json
✅ table_schema.json
✅ worldbank_schema.json
✅ my_custom_schema.json
✅ SCHEMA.JSON (case-insensitive)
✅ data_schema_v2.json
```

**Pattern**: Any `.json` file with "schema" in the name (case-insensitive)

## 🔍 How It Works

### 1. When Loading a CSV File

```python
load_csv_to_bigquery_from_gcs(
    dataset_name="worldbank_staging_dataset",
    bucket_name="my-bucket",
    file_path="data/countries.csv"
)
```

**The agent will:**
1. Look in the same directory as the CSV file (`data/`)
2. Find ALL `.json` files with "schema" in the name
3. Use the **first schema file found**
4. Look for the table definition in that schema file
5. Fall back to auto-detection if:
   - No schema file found
   - Schema file doesn't have that table definition
   - Error reading schema file

### 2. Search Priority

If multiple schema files exist, it uses the **first one alphabetically**:

```
gs://bucket/data/
  ├── a_schema.json          ← Uses this (first alphabetically)
  ├── source_schema.json
  └── z_schema.json
```

## 📋 Schema File Format

The schema file should be a JSON object with table names as keys:

```json
{
  "countries": [
    {"name": "country_code", "type": "STRING", "mode": "REQUIRED"},
    {"name": "country_name", "type": "STRING", "mode": "NULLABLE"},
    {"name": "region", "type": "STRING", "mode": "NULLABLE"}
  ],
  "indicators": [
    {"name": "indicator_code", "type": "STRING", "mode": "REQUIRED"},
    {"name": "indicator_name", "type": "STRING", "mode": "NULLABLE"}
  ]
}
```

## 🔎 Discovering Schema Files

### Using Standalone Agent

```bash
adk run agents/staging_loader_agent

> Find schema files in my-bucket under data/
```

### Using Orchestration Agent

```bash
adk run agents/orchestration

> Find schema files in my-bucket
```

### Programmatic Usage

```python
from agents.staging_loader_agent.tools.staging_loader_tools import find_schema_files_in_gcs

result = find_schema_files_in_gcs(
    bucket_name="my-bucket",
    prefix="data/"  # Optional: search in specific folder
)

# Returns:
{
  "status": "success",
  "bucket": "my-bucket",
  "prefix": "data/",
  "schema_files": [
    {
      "path": "data/source_schema.json",
      "name": "source_schema.json",
      "size_bytes": 1234,
      "updated": "2025-12-16T10:30:00Z"
    }
  ],
  "count": 1
}
```

## 📂 Directory Structure Examples

### Example 1: Schema at Root

```
gs://my-bucket/
  ├── worldbank_schema.json    ← Schema file
  ├── countries.csv
  ├── indicators.csv
  └── gdp.csv
```

**Load command:**
```
load_staging_data(
    dataset_name="staging",
    bucket_name="my-bucket",
    file_path="countries.csv"
)
```

✓ Finds `worldbank_schema.json`
✓ Uses schema for `countries` table

### Example 2: Schema in Subfolder

```
gs://my-bucket/data/
  ├── source_schema.json       ← Schema file
  ├── countries.csv
  └── indicators.csv
```

**Load command:**
```
load_staging_data(
    dataset_name="staging",
    bucket_name="my-bucket",
    file_path="data/countries.csv"
)
```

✓ Finds `data/source_schema.json`
✓ Uses schema for `countries` table

### Example 3: Multiple Schema Files

```
gs://my-bucket/data/
  ├── main_schema.json         ← Uses this (first found)
  ├── backup_schema.json
  ├── countries.csv
  └── indicators.csv
```

**Load command:**
```
load_staging_data(
    dataset_name="staging",
    bucket_name="my-bucket",
    file_path="data/countries.csv"
)
```

✓ Finds `main_schema.json` (alphabetically first)
✓ Uses that schema

### Example 4: No Schema File

```
gs://my-bucket/data/
  ├── countries.csv
  └── indicators.csv
```

**Load command:**
```
load_staging_data(
    dataset_name="staging",
    bucket_name="my-bucket",
    file_path="data/countries.csv"
)
```

ℹ️ No schema file found
✓ Falls back to BigQuery auto-detection

## 🎯 Best Practices

### 1. Use Descriptive Names

**Good:**
```
✅ worldbank_schema.json
✅ source_data_schema.json
✅ staging_schema_v2.json
```

**Works but less clear:**
```
⚠️ schema.json  (generic)
⚠️ s.json       (too short, but works if contains "schema" in content)
```

### 2. One Schema File Per Directory

For clarity, use one schema file per directory:

```
gs://bucket/
  ├── worldbank/
  │   ├── worldbank_schema.json
  │   └── *.csv files
  └── lending/
      ├── lending_schema.json
      └── *.csv files
```

### 3. Include All Tables

Put all table definitions in one schema file:

```json
{
  "countries": [...],
  "indicators": [...],
  "gdp": [...],
  "population": [...]
}
```

### 4. Discover Before Loading

Always check what schema files exist first:

```
User: Find schema files in my-bucket

Agent: Found 2 schema files:
       1. data/source_schema.json (2KB)
       2. archive/old_schema.json (1KB)

User: Load data/countries.csv to staging

Agent: Loading with schema from data/source_schema.json...
```

## 🔧 Workflow Example

### Complete Loading Workflow

```
# Step 1: Discover schema files
User: Find schema files in my-data-bucket under worldbank/

Agent: Found 1 schema file:
       - worldbank/source_schema.json (3.2KB)
       Contains definitions for 8 tables

# Step 2: Load data
User: Load worldbank/countries.csv to worldbank_staging_dataset

Agent: [Finds worldbank/source_schema.json automatically]
       [Uses schema definition for 'countries' table]
       ✓ Loaded 195 rows into worldbank_staging_dataset.countries

# Step 3: Load more files
User: Load worldbank/indicators.csv to worldbank_staging_dataset

Agent: [Uses same worldbank/source_schema.json]
       [Uses schema definition for 'indicators' table]
       ✓ Loaded 1,429 rows into worldbank_staging_dataset.indicators
```

## 🚨 Fallback Behavior

The agent gracefully handles missing or incomplete schemas:

### Scenario 1: Schema File But Table Not Defined

```json
// source_schema.json
{
  "countries": [...],
  "indicators": [...]
  // "gdp" is NOT defined
}
```

```
User: Load gdp.csv

Agent: Warning: Schema file found, but no entry for table 'gdp'
       Falling back to auto-detection
       ✓ Loaded 5,000 rows (schema auto-detected)
```

### Scenario 2: Schema File Parsing Error

```
User: Load countries.csv

Agent: Warning: Error parsing schema file (invalid JSON)
       Falling back to auto-detection
       ✓ Loaded 195 rows (schema auto-detected)
```

### Scenario 3: No Schema File

```
User: Load countries.csv

Agent: No schema file found
       Using BigQuery auto-detection
       ✓ Loaded 195 rows (schema auto-detected)
```

## 📊 Summary

**Flexibility:**
- ✅ Finds ANY file with "schema" in name
- ✅ Case-insensitive search
- ✅ Works in any directory structure

**Reliability:**
- ✅ Graceful fallback to auto-detection
- ✅ Clear logging of what schema was used
- ✅ Handles errors without failing

**Discoverability:**
- ✅ `find_schema_files()` to see what's available
- ✅ Shows file names, sizes, and paths
- ✅ Works through orchestration or standalone

**Your workflow is now flexible and doesn't depend on rigid file naming!** 🎉

---

**Updated**: December 16, 2025
**Feature**: Flexible Schema Detection
**Status**: ✅ Implemented and Integrated

