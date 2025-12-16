# Schema Mapping Agent

An intelligent Vertex AI agent that automatically analyzes BigQuery table schemas and generates ETL mappings with SQL transformation code.

## Overview

This agent helps data engineers create accurate schema mappings between source (staging) and target (analytics) tables in BigQuery. It uses AI to understand semantic relationships between columns, validates type compatibility, and generates production-ready SQL code.

### Key Features

- 🤖 **Intelligent Mapping**: Uses Gemini AI to understand column relationships beyond exact name matches
- 🔍 **Schema Analysis**: Automatically introspects BigQuery tables and analyzes column metadata
- 🎯 **Type Safety**: Validates source→target type compatibility and generates appropriate CAST statements
- 📊 **Multi-Format Output**: Generates SQL, Markdown reports, and interactive HTML visualizations
- 💬 **Interactive Refinement**: Chat-based interface to review and adjust mappings
- ✅ **Review/Approve Workflow**: Present mappings for user validation before finalization
- 🚀 **Production Ready**: Generates INSERT, MERGE, and DBT-style SQL

## Quick Start

### Prerequisites

1. Python 3.11 or higher
2. Google Cloud Project with BigQuery access
3. Authenticated with Google Cloud:
   ```bash
   gcloud auth application-default login
   ```

### Installation

```bash
# Install dependencies
uv sync

# Or using pip
pip install -e .
```

### Running Locally

```bash
# Interactive mode (chat with the agent)
python schema_mapping/test_local.py

# Direct mode (generate mapping directly)
python schema_mapping/test_local.py --mode direct \
  --source "project.dataset.source_table" \
  --target "project.dataset.target_table"
```

### Example Usage

```python
from schema_mapping.agent import root_agent

# Chat with the agent
response = root_agent.generate_response(
    message="Create a schema mapping from ccibt-hack25ww7-750.test_staging_dataset.borrower to ccibt-hack25ww7-750.test_dataset.dim_borrower"
)
print(response)
```

## Usage Guide

### 1. Basic Schema Mapping

The agent will analyze both tables and generate:
- SQL transformation code
- Markdown mapping report
- HTML visualization

```
You: Create a schema mapping from ccibt-hack25ww7-750.test_staging_dataset.borrower 
     to ccibt-hack25ww7-750.test_dataset.dim_borrower

Agent: I've analyzed both tables and created a schema mapping.
       
       📊 Summary:
       - Mapped 12/12 columns (100% coverage)
       - 12 high confidence mappings
       - 2 type conversions needed
       
       📄 Generated Files:
       - SQL: schema_mapping/output/mapping_dim_borrower.sql
       - Report: schema_mapping/output/mapping_report_dim_borrower.md
       - Visualization: schema_mapping/output/mapping_viz_dim_borrower.html
```

### 2. Review and Refine

```
You: Show me the mapping for the annual_revenue column

Agent: The annual_revenue column mapping:
       - Source: annual_revenue (STRING from CSV)
       - Target: annual_revenue (NUMERIC)
       - Transformation: SAFE_CAST to NUMERIC
       - Confidence: High (100% name match)
       
       This mapping converts the string revenue values to numeric.
       I'm using SAFE_CAST to handle any invalid values gracefully.

You: Change that to use regular CAST instead

Agent: Updated! I've regenerated the SQL with CAST instead of SAFE_CAST 
       for annual_revenue. Note that this will fail if any invalid numeric 
       values are encountered.
```

### 3. Batch Processing (Process Entire Datasets)

**List all tables in a dataset:**
```
You: List all tables in ccibt-hack25ww7-750.test_staging_dataset
```

**Discover matching table pairs:**
```
You: Discover table pairs between ccibt-hack25ww7-750.test_staging_dataset 
     and ccibt-hack25ww7-750.test_dataset
```

**Process all tables at once:**
```
You: Map all tables from ccibt-hack25ww7-750.test_staging_dataset 
     to ccibt-hack25ww7-750.test_dataset

Agent: 🚀 Batch Processing 5 Table Pairs
       
       ✅ 1/5: borrower → dim_borrower
           Mapped 12/12 columns, 12 high confidence
       ✅ 2/5: loan → dim_loan
           Mapped 18/18 columns, 16 high confidence
       ...
       
       📊 Batch Processing Complete:
       - ✅ Successful: 5
       - ❌ Failed: 0
```

### 4. Advanced Features

**Get table information:**
```
You: Show me details about ccibt-hack25ww7-750.test_staging_dataset.borrower
```

**Analyze specific columns:**
```
You: Analyze the borrower_id column in the source table
```

**Generate MERGE instead of INSERT:**
```
You: Generate a MERGE statement using borrower_id as the key
```

**Generate DBT model:**
```
You: Generate a DBT model for these tables
You: Create a DBT model from source to target
```

**Get sample data:**
```
You: Show me sample data from the target table
```

## Output Files

### 1. SQL File (`mapping_<table>.sql`)

Standard INSERT INTO ... SELECT format:

```sql
-- Schema Mapping: source_table → target_table
-- Generated: 2025-12-16 10:30:00

INSERT INTO `project.dataset.target_table` (
  `borrower_id`,
  `borrower_name`,
  ...
)

SELECT
  SAFE_CAST(`borrower_id` AS INT64) AS `borrower_id`,  -- CAST_TO_INT64
  `borrower_name` AS `borrower_name`,                  -- DIRECT
  ...
FROM `project.dataset.source_table`;
```

### 1b. DBT Model File (`dbt_<table>.sql`)

DBT (Data Build Tool) format with Jinja2 config:

```sql
{{
  config(
    materialized='table',
    schema='target_dataset',
    alias='dim_borrower'
  )
}}

SELECT
  SAFE_CAST(`borrower_id` AS INT64) AS `borrower_id`,
  `borrower_name` AS `borrower_name`,
  ...
FROM `project.dataset.source_table`
```

### 2. Markdown Report (`mapping_report_<table>.md`)

A comprehensive report including:
- Mapping summary with statistics
- Column-by-column mapping table
- Detailed transformation explanations
- Warnings for unmapped columns
- Recommendations and next steps

### 3. HTML Visualization (`mapping_viz_<table>.html`)

An interactive web page with:
- Visual schema comparison
- Color-coded confidence levels
- Expandable mapping details
- Sample values and analysis

## Deployment to Vertex AI

### Deploy the Agent

```bash
# Set up environment
export GCP_PROJECT="your-project-id"

# Check IAM permissions
python schema_mapping/deploy_vertex.py --action permissions

# Deploy
python schema_mapping/deploy_vertex.py --action deploy
```

### Access the Deployed Agent

Once deployed, access your agent through:

1. **Google Cloud Console**
   - Navigate to Vertex AI > Agent Builder
   - Find "Schema Mapping Agent"
   - Use the built-in chat interface

2. **Python SDK**
   ```python
   from google.cloud import aiplatform
   
   aiplatform.init(project="your-project", location="us-central1")
   
   # Use the agent
   # (See Vertex AI Agent SDK documentation)
   ```

3. **REST API**
   - Use Vertex AI Agent REST API endpoints
   - See Google Cloud documentation for details

## Configuration

Set environment variables to customize behavior:

```bash
# BigQuery settings
export GCP_PROJECT="your-project-id"

# Mapping preferences
export SIMILARITY_THRESHOLD=80          # Column name similarity (0-100)
export USE_SAFE_CAST=true              # Use SAFE_CAST vs CAST

# Output settings
export OUTPUT_DIR="schema_mapping/output"
export GENERATE_HTML=true
export GENERATE_MARKDOWN=true

# Vertex AI settings
export VERTEX_AI_LOCATION="us-central1"
```

Or modify `schema_mapping/config.py` directly.

## Example: Commercial Lending Dataset

This project includes a sample Commercial Lending dataset. Here's how to use it:

```bash
# 1. Load the sample data to BigQuery (if not already loaded)
# (Use BigQuery console or bq command-line tool)

# 2. Create staging and target datasets
bq mk --dataset your-project:test_staging_dataset
bq mk --dataset your-project:test_dataset

# 3. Run the agent
python schema_mapping/test_local.py

# 4. In the interactive prompt
You: Create a schema mapping from your-project.test_staging_dataset.borrower 
     to your-project.test_dataset.dim_borrower
```

## Hackathon Demo Script

Perfect for demonstrating the agent's capabilities:

```bash
# 1. Start the agent
python schema_mapping/test_local.py

# 2. Type 'demo' or 'test' to use default tables
You: demo

# 3. The agent will:
#    - Connect to BigQuery
#    - Analyze both schemas
#    - Generate mappings
#    - Create all output files

# 4. Show the outputs:
#    - Open the HTML visualization in a browser
#    - Review the Markdown report
#    - Examine the SQL code

# 5. Demonstrate refinement:
You: Show me columns with type conversions
You: Change borrower_id to use regular CAST
You: Generate a MERGE statement instead

# 6. Approve the mapping:
You: This looks good, I approve this mapping
```

## Architecture

```
schema_mapping/
├── agent.py              # Main agent with Gemini AI
├── bigquery_tools.py     # BigQuery schema introspection
├── schema_analyzer.py    # Mapping logic and similarity matching
├── sql_generator.py      # SQL code generation (INSERT, MERGE, DBT)
├── report_generator.py   # Markdown report generation
├── visualizer.py         # HTML visualization generation
├── config.py            # Configuration management
├── test_local.py        # Local testing script
├── deploy_vertex.py     # Vertex AI deployment
└── output/              # Generated files
```

## Troubleshooting

### Authentication Issues

```bash
# Make sure you're authenticated
gcloud auth application-default login

# Or use a service account
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

### Table Not Found

- Verify table names are in format: `project.dataset.table`
- Check that tables exist in BigQuery
- Ensure you have read permissions

### Import Errors

```bash
# Reinstall dependencies
uv sync --reinstall

# Or with pip
pip install -e . --force-reinstall
```

### No Output Files Generated

- Check that `schema_mapping/output/` directory exists
- Verify write permissions
- Look for error messages in console output

## Integration with Larger ETL Pipeline

This agent is designed to be part of a larger ETL framework:

```python
# Example: Automated ETL pipeline
from schema_mapping.agent import map_schemas

# 1. Discover tables
source_tables = discover_staging_tables()
target_tables = discover_target_tables()

# 2. Generate mappings for each pair
for source, target in zip(source_tables, target_tables):
    mapping = map_schemas(source, target)
    
# 3. Review and approve (could be automated based on confidence)
    
# 4. Execute SQL transformations
    
# 5. Validate data quality
```

## Future Enhancements

- [ ] Support for complex transformations (CONCAT, SPLIT, etc.)
- [ ] Data quality rules and validation
- [ ] Automated testing of generated SQL
- [ ] Integration with Apache Airflow / DBT
- [ ] Support for other data warehouses (Snowflake, Redshift)
- [ ] ML-based column matching using embeddings
- [ ] Historical mapping versioning

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the example outputs
3. Examine the code comments
4. Check Google Cloud documentation for Vertex AI and BigQuery

## License

Part of the GPT Hackathon PrimeTime project.

---

**Built with:** Google Vertex AI, Gemini 2.0, BigQuery, and ADK

