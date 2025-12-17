# ETL Agent

Generates and executes ETL SQL scripts from JSON schema mapping rules.

## 🎯 What It Does

The ETL Agent is the **final stage** in the data integration pipeline. It:

1. **Takes JSON mapping rules** from the Schema Mapping Agent
2. **Generates SQL INSERT statements** to load data from staging to target tables
3. **Handles complex patterns**:
   - Direct 1-to-1 table mappings
   - UNION ALL (combining multiple sources)
   - PIVOT/Aggregation (wide tables)
   - Column transformations
   - Default values for unmapped columns
4. **Executes SQL in BigQuery** (after human review!)

## 🚀 Quick Start

### Option 1: Through Orchestration (Recommended)

```bash
adk run agents/orchestration

# Complete workflow
> Run complete workflow from staging to target, then generate ETL SQL

# Step-by-step
> Generate schema mapping from worldbank_staging to worldbank_target
> Generate ETL SQL from the mapping
[Review SQL]
> Execute the ETL SQL in worldbank_target
```

### Option 2: Standalone Agent

```bash
adk run agents/etl_agent

> Generate ETL SQL from this mapping JSON: {...}
[Shows generated SQL]

> Execute this SQL in my_target_dataset
[Executes after confirmation]
```

### Option 3: Programmatic Usage

```python
from agents.etl_agent.tools.gen_etl_sql import (
    generate_etl_sql_from_json_string,
    execute_sql
)

# Generate SQL
mapping_json = '{"mapping": {...}}'
sql_scripts = generate_etl_sql_from_json_string(mapping_json)
print(sql_scripts)

# Review, then execute
result = execute_sql(
    query_sql=sql_scripts,
    dataset_name="my_target_dataset"
)
print(result)
```

## 📋 Configuration

### Environment Variables

```bash
# Required: GCP Project ID
export GCP_PROJECT_ID=your-project-id
# OR
export GOOGLE_CLOUD_PROJECT=your-project-id

# Optional: Location (default: us-central1)
export GOOGLE_CLOUD_LOCATION=us-central1
```

### .env File

```env
GCP_PROJECT_ID=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

## 🔧 How It Works

### Input: JSON Mapping Rules

The ETL agent expects JSON mapping rules from the Schema Mapping Agent:

```json
{
  "mapping": {
    "metadata": {
      "source_dataset": "worldbank_staging_dataset",
      "target_dataset": "worldbank_target_dataset"
    },
    "mappings": [
      {
        "target_table": "worldbank_target.dim_country",
        "source_table": "worldbank_staging.countries",
        "column_mappings": [
          {
            "target_column": "country_code",
            "source_column": "country_code"
          },
          {
            "target_column": "country_name",
            "source_column": "country_name"
          }
        ]
      }
    ]
  }
}
```

### Output: SQL INSERT Statements

```sql
-- ####################################################
-- #          Generated ETL SQL Script                #
-- ####################################################

-- Populating 'worldbank_target.dim_country' from 'worldbank_staging.countries'
INSERT INTO `worldbank_target.dim_country` (
    country_code, country_name, region
)
SELECT
    country_code AS country_code,
    country_name AS country_name,
    region AS region
FROM
    `worldbank_staging.countries`;

-- ------------------------------------------------------------------
```

## 📊 SQL Generation Patterns

### 1. Direct 1-to-1 Mapping (Dimension Tables)

**Input:**
```json
{
  "target_table": "target.dim_country",
  "source_table": "staging.countries",
  "column_mappings": [
    {"target_column": "country_code", "source_column": "country_code"},
    {"target_column": "country_name", "source_column": "country_name"}
  ]
}
```

**Output:**
```sql
INSERT INTO `target.dim_country` (
    country_code, country_name
)
SELECT
    country_code AS country_code,
    country_name AS country_name
FROM
    `staging.countries`;
```

### 2. UNION ALL (Multiple Sources → One Table)

**Input:**
```json
{
  "target_table": "target.fact_indicator_values",
  "source_table": "staging.gdp, staging.population, staging.life_expectancy",
  "column_mappings": [
    {"target_column": "country_code", "source_column": "country_code"},
    {"target_column": "year", "source_column": "year"},
    {
      "target_column": "indicator_code",
      "transformation": "WHERE indicator_code = 'NY.GDP.MKTP.CD'"
    },
    {"target_column": "numeric_value", "source_column": "gdp_value"}
  ]
}
```

**Output:**
```sql
INSERT INTO `target.fact_indicator_values` (
    country_code, year, indicator_code, numeric_value
)
SELECT country_code AS country_code, year AS year, 'NY.GDP.MKTP.CD' AS indicator_code, gdp_value AS numeric_value 
FROM `staging.gdp`
UNION ALL
SELECT country_code AS country_code, year AS year, 'SP.POP.TOTL' AS indicator_code, population AS numeric_value 
FROM `staging.population`
UNION ALL
SELECT country_code AS country_code, year AS year, 'SP.DYN.LE00.IN' AS indicator_code, life_expectancy AS numeric_value 
FROM `staging.life_expectancy`;
```

### 3. PIVOT (Aggregation → Wide Table)

**Input:**
```json
{
  "target_table": "target.agg_country_year",
  "source_table": "target.fact_indicator_values",
  "column_mappings": [
    {"target_column": "country_code", "source_column": "country_code"},
    {"target_column": "year", "source_column": "year"},
    {
      "target_column": "gdp",
      "transformation": "WHERE indicator_code = 'NY.GDP.MKTP.CD'"
    },
    {
      "target_column": "population",
      "transformation": "WHERE indicator_code = 'SP.POP.TOTL'"
    },
    {
      "target_column": "gdp_per_capita",
      "source_column": "UNMAPPED"
    }
  ]
}
```

**Output:**
```sql
INSERT INTO `target.agg_country_year` (
    country_code, year, gdp, population, gdp_per_capita
)
SELECT
    country_code AS country_code,
    year AS year,
    MAX(IF(indicator_code = 'NY.GDP.MKTP.CD', numeric_value, NULL)) AS gdp,
    MAX(IF(indicator_code = 'SP.POP.TOTL', numeric_value, NULL)) AS population,
    SAFE_DIVIDE(
        MAX(IF(indicator_code = 'NY.GDP.MKTP.CD', numeric_value, NULL)), 
        MAX(IF(indicator_code = 'SP.POP.TOTL', numeric_value, NULL))
    ) AS gdp_per_capita
FROM
    `target.fact_indicator_values`
GROUP BY
    country_code, year;
```

### 4. Column Transformations

**Input:**
```json
{
  "target_column": "created_at",
  "transformation": "CURRENT_TIMESTAMP()"
}
```

**Output:**
```sql
CURRENT_TIMESTAMP() AS created_at
```

### 5. Default Values for Unmapped Columns

**Input:**
```json
{
  "target_column": "created_at",
  "source_column": "UNMAPPED"
}
```

**Output:**
```sql
CURRENT_TIMESTAMP() /* Default for unmapped column */ AS created_at
```

## 🔐 Safety Features

### Human-in-the-Loop Execution

The ETL agent **requires human review** before executing SQL:

1. ✅ SQL is generated and presented to the user
2. ✅ User explicitly reviews and approves
3. ✅ Only then is SQL executed
4. ✅ Agent instructions enforce this pattern

**Example Workflow:**
```
User: Generate ETL SQL

Agent: [Generates SQL]
       Here are the SQL scripts:
       [Shows full SQL]
       
       ⚠️  IMPORTANT: Please review the SQL before executing.
       Would you like me to execute this SQL?

User: Yes, execute it

Agent: [Executes SQL]
       ✓ Data loaded successfully!
```

### SQL Repair (Best Effort)

If the JSON mapping is malformed, the agent attempts to repair it:

1. Removes dangling partial lines
2. Force-closes open structures
3. Removes trailing commas
4. Adds warning to generated SQL

**Warning in SQL:**
```sql
-- WARNING: The initial JSON was malformed and has been automatically repaired.
-- Please review the generated SQL carefully, as it may be based on incomplete mapping rules.
```

## 🎮 Usage Examples

### Example 1: Complete Workflow Through Orchestration

```bash
adk run agents/orchestration

User: I want to load data from staging to target

Agent: I'll help you with the complete workflow. Let me:
       1. Generate schema mapping
       2. Validate the data
       3. Generate ETL SQL
       4. Execute (after your review)

User: Sounds good

Agent: [Generates mapping]
       ✓ Created mapping for 5 tables
       
       [Validates data]
       ✓ Validation passed with 2 warnings
       
       [Generates SQL]
       ✓ Generated ETL SQL scripts
       
       Here's the SQL:
       [Shows SQL]
       
       Would you like me to execute this?

User: Yes

Agent: [Executes SQL]
       ✓ Data loaded into target tables!
```

### Example 2: Just ETL Generation

```bash
adk run agents/etl_agent

User: Generate ETL SQL from this mapping: {...}

Agent: [Generates SQL]
       Here are the SQL INSERT statements:
       [Shows SQL]
       
       The SQL is ready. Would you like to execute it?

User: Show me the SQL for dim_country

Agent: [Shows specific SQL for that table]

User: Execute it in worldbank_target

Agent: [Executes SQL]
       ✓ Loaded data into worldbank_target.dim_country
```

### Example 3: Programmatic Usage

```python
import os
import json
from dotenv import load_dotenv
from agents.etl_agent.tools.gen_etl_sql import (
    generate_etl_sql_from_json_string,
    execute_sql
)

# Load environment
load_dotenv()

# Load mapping from file
with open("mapping.json", "r") as f:
    mapping_data = json.load(f)

# Generate SQL
mapping_json = json.dumps(mapping_data)
sql_scripts = generate_etl_sql_from_json_string(mapping_json)

# Save SQL to file
with open("etl_scripts.sql", "w") as f:
    f.write(sql_scripts)

print("Generated SQL saved to etl_scripts.sql")
print("\nReview the SQL, then execute with:")
print("  execute_sql(sql_scripts, 'my_target_dataset')")

# After review, execute
# result = execute_sql(sql_scripts, "my_target_dataset")
# print(result)
```

## 🧪 Testing

### Test Locally

```bash
# Set environment variables
export GCP_PROJECT_ID=your-project-id

# Run test
python agents/orchestration/test_etl_integration.py
```

### Test with ADK

```bash
adk run agents/etl_agent

# Test SQL generation
> Generate ETL SQL from this mapping: {"mapping": {...}}

# Test execution (dry run)
> Show me what SQL would be executed for dataset X
```

## 📦 Dependencies

```txt
google-adk>=1.0.0
python-dotenv==1.0.0
google-cloud-bigquery>=3.13.0
```

## 🔧 Tools Reference

### `generate_etl_sql_from_json_string(mapping_rules_json: str) -> str`

Generates ETL SQL scripts from JSON mapping rules.

**Args:**
- `mapping_rules_json`: JSON string with mapping rules

**Returns:**
- SQL INSERT statements as a string

**Example:**
```python
sql = generate_etl_sql_from_json_string('{"mapping": {...}}')
```

### `execute_sql(query_sql: str, dataset_name: str, hardcoded_dataset_to_replace: str = None) -> str`

Executes SQL in BigQuery.

**Args:**
- `query_sql`: SQL to execute
- `dataset_name`: Target dataset
- `hardcoded_dataset_to_replace`: Optional dataset name to replace in SQL

**Returns:**
- Execution results as a string

**Example:**
```python
result = execute_sql(
    query_sql=sql_scripts,
    dataset_name="my_target_dataset"
)
```

## 🎯 Best Practices

### 1. Always Review SQL Before Executing

```
✅ DO: Review SQL → Approve → Execute
❌ DON'T: Auto-execute without review
```

### 2. Test with Small Datasets First

```
✅ DO: Test with 1-2 tables first
❌ DON'T: Execute all tables at once without testing
```

### 3. Save Generated SQL

```python
# Save for review and version control
with open("etl_scripts.sql", "w") as f:
    f.write(sql_scripts)
```

### 4. Use Orchestration for Complete Workflows

```
✅ DO: Use orchestration agent for end-to-end workflows
❌ DON'T: Manually coordinate multiple agents
```

### 5. Handle Errors Gracefully

```python
try:
    result = execute_sql(sql, "target_dataset")
    print(f"Success: {result}")
except Exception as e:
    print(f"Error: {e}")
    # Review SQL and fix issues
```

## 🐛 Troubleshooting

### Error: "GCP_PROJECT_ID environment variable not set"

**Solution:**
```bash
export GCP_PROJECT_ID=your-project-id
# OR
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### Error: "Could not decode JSON"

**Solution:**
- Check JSON syntax
- Ensure mapping structure is correct
- Agent will attempt auto-repair, but may need manual fix

### Error: "Table not found"

**Solution:**
- Ensure staging tables exist
- Check dataset names in mapping
- Verify BigQuery permissions

### Error: "Column not found"

**Solution:**
- Verify column names in mapping
- Check source table schema
- Regenerate mapping with Schema Mapping Agent

## 📚 Related Documentation

- [Orchestration Agent](../orchestration/README.md)
- [Schema Mapping Agent](../schema_mapping/README.md)
- [Validation Agent](../validation/README.md)
- [Staging Loader Agent](../staging_loader_agent/README.md)

## 🎉 Summary

The ETL Agent is the **final stage** of the data integration pipeline:

```
Load → Map → Validate → ETL
  ↓      ↓       ↓       ↓
 CSV   JSON   Report   SQL
```

**Key Features:**
- ✅ Generates SQL from JSON mappings
- ✅ Handles complex patterns (UNION, PIVOT, etc.)
- ✅ Human-in-the-loop execution
- ✅ Integrates seamlessly with orchestration
- ✅ Safe and flexible

**Ready to load your data!** 🚀

---

**Updated**: December 16, 2025  
**Version**: 1.0  
**Status**: ✅ Production Ready

