# Complete Data Integration Workflow Guide

## 🎯 Overview

This guide shows you how to use the **Orchestration Agent** to run complete data integration workflows with all 4 stages:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION AGENT                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   STAGE 1    │  │   STAGE 2    │  │   STAGE 3    │        │
│  │              │  │              │  │              │        │
│  │   Staging    │→ │   Schema     │→ │  Validation  │→      │
│  │   Loader     │  │   Mapping    │  │              │        │
│  │              │  │              │  │              │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│         ┌──────────────┐                                       │
│         │   STAGE 4    │                                       │
│         │              │                                       │
│         │     ETL      │   • Generate SQL                      │
│         │   Agent      │   • Review (Human-in-Loop)            │
│         │              │   • Execute                           │
│         └──────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

```bash
# Set environment variables
export GCP_PROJECT_ID=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1

# OR use .env file
cat > .env << EOF
GCP_PROJECT_ID=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
EOF
```

### Run the Orchestration Agent

```bash
adk run agents/orchestration
```

## 📋 Complete Workflow Examples

### Example 1: Full End-to-End Workflow

```
User: I want to run a complete data integration workflow.
      Source: worldbank_staging_dataset
      Target: worldbank_target_dataset

Orchestrator: I'll run the complete workflow for you:

              STAGE 1: Loading Staging Data (if needed)
              ✓ Data already loaded

              STAGE 2: Generating Schema Mapping
              ✓ Generated mapping for 5 tables:
                - dim_country (3 columns)
                - dim_indicator (4 columns)
                - dim_time (3 columns)
                - fact_indicator_values (5 columns)
                - agg_country_year (7 columns)
              
              Mapping ID: worldbank_staging_dataset_to_worldbank_target_dataset

              STAGE 3: Validating Data
              ✓ Validation complete
              - 5 tables validated
              - 2 warnings found
              - 0 errors found

              STAGE 4: Generating ETL SQL
              ✓ Generated SQL INSERT statements
              
              ETL ID: worldbank_staging_dataset_to_worldbank_target_dataset_etl

              Here's a preview of the SQL:
              
              -- Populating 'dim_country' from 'countries'
              INSERT INTO `worldbank_target.dim_country` (...)
              SELECT ... FROM `worldbank_staging.countries`;
              
              [... more SQL ...]

              ⚠️  IMPORTANT: Please review the SQL before executing.
              
              Would you like me to:
              1. Show you the complete SQL
              2. Execute the SQL (after your review)
              3. Save the SQL to a file

User: Execute the SQL

Orchestrator: [Executes SQL]
              ✓ ETL SQL executed successfully!
              ✓ Data loaded into worldbank_target dataset
              
              Execution ID: worldbank_staging_dataset_to_worldbank_target_dataset_etl_execution
              
              Summary:
              - 5 tables loaded
              - Workflow ID: workflow_20251216_103000
              
              Your data integration is complete! 🎉
```

### Example 2: Step-by-Step with Review

```
User: Load data/countries.csv from my-bucket to worldbank_staging_dataset

Orchestrator: STAGE 1: Loading Staging Data
              ✓ Loaded 195 rows into worldbank_staging_dataset.countries
              Load ID: worldbank_staging_dataset_countries

User: Generate schema mapping from worldbank_staging to worldbank_target

Orchestrator: STAGE 2: Generating Schema Mapping
              ✓ Generated mapping for 5 tables
              Mapping ID: worldbank_staging_to_worldbank_target
              
              Would you like to:
              1. Review the mapping
              2. Proceed with validation

User: Review the mapping

Orchestrator: [Shows detailed mapping]
              
              Mapping Details:
              
              Table: dim_country
              Source: worldbank_staging.countries
              Columns:
              - country_code → country_code (STRING)
              - country_name → country_name (STRING)
              - region → region (STRING)
              
              [... more tables ...]

User: Validate it

Orchestrator: STAGE 3: Validating Data
              ✓ Validation complete
              
              Results:
              - dim_country: ✓ Pass (195 rows)
              - dim_indicator: ⚠️  Warning (1,429 rows, 2 nulls in optional field)
              - fact_indicator_values: ✓ Pass (50,000 rows)
              
              Validation ID: worldbank_staging_to_worldbank_target_validation

User: Generate ETL SQL

Orchestrator: STAGE 4: Generating ETL SQL
              ✓ Generated SQL INSERT statements
              ETL ID: worldbank_staging_to_worldbank_target_etl
              
              [Shows SQL preview]
              
              ⚠️  Please review the SQL before executing.

User: Show me the complete SQL

Orchestrator: [Shows complete SQL]
              
              -- ####################################################
              -- #          Generated ETL SQL Script                #
              -- ####################################################
              
              -- Populating 'dim_country' from 'countries'
              INSERT INTO `worldbank_target.dim_country` (
                  country_code, country_name, region
              )
              SELECT
                  country_code AS country_code,
                  country_name AS country_name,
                  region AS region
              FROM
                  `worldbank_staging.countries`;
              
              [... complete SQL ...]

User: Execute it in worldbank_target

Orchestrator: [Executes SQL]
              ✓ ETL SQL executed successfully!
              ✓ Data loaded into worldbank_target dataset
              
              Execution Summary:
              - Tables loaded: 5
              - Rows inserted: ~51,624
              - Execution time: 12.3 seconds
              
              Workflow complete! 🎉
```

### Example 3: Discover Schema Files First

```
User: Find schema files in my-data-bucket

Orchestrator: STAGE 1: Discovering Schema Files
              
              Found 2 schema files in 'my-data-bucket':
              
              1. worldbank/source_schema.json (3.2 KB)
                 Updated: 2025-12-15T10:30:00Z
              
              2. archive/old_schema.json (1.5 KB)
                 Updated: 2025-11-01T08:15:00Z
              
              The first schema file will be used automatically when loading data.

User: Load worldbank/countries.csv to worldbank_staging

Orchestrator: STAGE 1: Loading Staging Data
              
              ✓ Found schema file: worldbank/source_schema.json
              ✓ Using schema definition for 'countries' table
              ✓ Loaded 195 rows into worldbank_staging.countries
              
              Load ID: worldbank_staging_countries

User: Continue with the full workflow

Orchestrator: [Continues with stages 2-4...]
```

## 🎮 Available Commands

### Workflow Management

```
# Run complete workflow
> Run complete workflow from [source] to [target]

# Check workflow status
> Show me workflow status for workflow_123
> List all workflows

# Get workflow details
> What workflows have I run?
> Show me the latest workflow
```

### Stage 1: Data Loading

```
# Load single file
> Load data/countries.csv from my-bucket to worldbank_staging

# Find schema files
> Find schema files in my-bucket
> Find schema files in my-bucket under data/

# Check loads
> List all staging loads
> Show me load details for worldbank_staging_countries
```

### Stage 2: Schema Mapping

```
# Generate mapping
> Generate schema mapping from worldbank_staging to worldbank_target
> Map worldbank_staging to worldbank_target in FIX mode

# Review mappings
> List all mappings
> Show me mapping worldbank_staging_to_worldbank_target
> Get mapping details
```

### Stage 3: Validation

```
# Validate data
> Validate data using mapping worldbank_staging_to_worldbank_target
> Run validation in REPORT mode

# Review results
> Show me validation results
> Get validation details for worldbank_staging_to_worldbank_target_validation
```

### Stage 4: ETL

```
# Generate SQL
> Generate ETL SQL from mapping worldbank_staging_to_worldbank_target
> Create ETL scripts for the mapping

# Review SQL
> Show me the ETL SQL
> Get ETL SQL details for worldbank_staging_to_worldbank_target_etl
> List all ETL scripts

# Execute SQL
> Execute ETL worldbank_staging_to_worldbank_target_etl in worldbank_target
> Run the ETL SQL
```

## 📊 Workflow Tracking

### Workflow IDs

Every workflow gets a unique ID:
```
workflow_20251216_103000
```

Use this ID to:
- Track progress
- Get status updates
- Reference in future operations

### Workflow State

```
{
  "workflow_id": "workflow_20251216_103000",
  "created_at": "2025-12-16T10:30:00",
  "steps": [
    {
      "step": "staging_load",
      "status": "completed",
      "load_id": "worldbank_staging_countries",
      "timestamp": "2025-12-16T10:30:15"
    },
    {
      "step": "schema_mapping",
      "status": "completed",
      "mapping_id": "worldbank_staging_to_worldbank_target",
      "timestamp": "2025-12-16T10:31:00"
    },
    {
      "step": "validation",
      "status": "completed",
      "validation_id": "worldbank_staging_to_worldbank_target_validation",
      "timestamp": "2025-12-16T10:33:00"
    },
    {
      "step": "etl_sql_generation",
      "status": "completed",
      "etl_id": "worldbank_staging_to_worldbank_target_etl",
      "timestamp": "2025-12-16T10:34:00"
    },
    {
      "step": "etl_execution",
      "status": "completed",
      "execution_id": "worldbank_staging_to_worldbank_target_etl_execution",
      "timestamp": "2025-12-16T10:35:00"
    }
  ]
}
```

## 🔐 Safety & Best Practices

### 1. Always Review SQL Before Executing

```
✅ DO: Review → Approve → Execute
❌ DON'T: Auto-execute without review
```

### 2. Test with Small Datasets First

```
✅ DO: Test with 1-2 tables
❌ DON'T: Run full workflow on production data first
```

### 3. Use Workflow IDs for Tracking

```
✅ DO: Track workflows with IDs
❌ DON'T: Lose track of what you've run
```

### 4. Validate Before ETL

```
✅ DO: Validate → Review → ETL
❌ DON'T: Skip validation
```

### 5. Save Generated Artifacts

```
✅ DO: Save mappings and SQL for review
❌ DON'T: Rely only on in-memory state
```

## 🧪 Testing

### Test Locally

```bash
# Run test script
python agents/orchestration/test_etl_integration.py
```

### Test with ADK

```bash
adk run agents/orchestration

# Test each stage
> Load test data
> Generate test mapping
> Validate test data
> Generate test ETL SQL
```

## 🐛 Troubleshooting

### Issue: "GCP_PROJECT_ID not set"

**Solution:**
```bash
export GCP_PROJECT_ID=your-project-id
```

### Issue: "Mapping not found"

**Solution:**
```
> List all mappings
[Shows available mappings]
> Use the correct mapping ID
```

### Issue: "Table not found"

**Solution:**
1. Ensure staging data is loaded (Stage 1)
2. Check dataset names
3. Verify BigQuery permissions

### Issue: "Validation failed"

**Solution:**
1. Review validation results
2. Fix data quality issues
3. Regenerate mapping if needed
4. Re-run validation

### Issue: "SQL execution failed"

**Solution:**
1. Review the SQL
2. Check table schemas
3. Verify column names
4. Test with single table first

## 📚 Related Documentation

- [ETL Agent README](../etl_agent/README.md)
- [Schema Mapping Agent](../schema_mapping/README.md)
- [Validation Agent](../validation/README.md)
- [Staging Loader Agent](../staging_loader_agent/README.md)
- [ETL Integration Summary](../ETL_INTEGRATION_SUMMARY.md)

## 🎯 Common Use Cases

### Use Case 1: World Bank Data Integration

```
1. Load CSV files from GCS to staging
2. Generate schema mapping (staging → target)
3. Validate data quality
4. Generate and execute ETL SQL
5. Data ready for analytics!
```

### Use Case 2: Commercial Lending Data

```
1. Load loan, borrower, collateral data
2. Map to star schema (dims + facts)
3. Validate referential integrity
4. Execute ETL to load data warehouse
5. Business intelligence ready!
```

### Use Case 3: Incremental Data Updates

```
1. Load new data to staging
2. Reuse existing schema mapping
3. Validate new data
4. Execute ETL (append mode)
5. Target tables updated!
```

## 🎉 Summary

The Orchestration Agent provides a **complete, AI-powered data integration pipeline**:

**4 Stages:**
1. ✅ Load staging data from GCS
2. ✅ Generate intelligent schema mappings
3. ✅ Validate data quality
4. ✅ Generate and execute ETL SQL

**Key Features:**
- 🤖 AI-powered at every stage
- 🔐 Human-in-the-loop for safety
- 📊 Complete workflow tracking
- 🎯 Flexible (complete or step-by-step)
- 🚀 Production-ready

**Ready to integrate your data!** 🎉

---

**Updated**: December 16, 2025  
**Version**: 1.0  
**Status**: ✅ Production Ready

