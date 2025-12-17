# Quick Reference: Data Integration Pipeline

## 🚀 Quick Start

```bash
# 1. Set environment
export GCP_PROJECT_ID=your-project-id

# 2. Run orchestration
adk run agents/orchestration

# 3. Run complete workflow
> Run complete workflow from my_staging to my_target
```

## 📋 4-Stage Pipeline

```
STAGE 1: Staging Loader  →  Load CSV from GCS to BigQuery
STAGE 2: Schema Mapping  →  Generate AI-powered mappings
STAGE 3: Validation      →  Validate data quality
STAGE 4: ETL Agent       →  Generate & execute SQL
```

## 🎮 Common Commands

### Complete Workflow
```
> Run complete workflow from [source] to [target]
```

### Step-by-Step
```
> Load [file] from [bucket] to [dataset]
> Generate schema mapping from [source] to [target]
> Validate the mapping
> Generate ETL SQL from the mapping
> Execute the ETL SQL in [target]
```

### Discovery
```
> Find schema files in [bucket]
> List all workflows
> List all mappings
> List all ETL scripts
```

### Status & Details
```
> Show workflow status
> Show me the mapping
> Show me the SQL
> Get validation results
```

## 🔧 Environment Variables

```bash
# Required
export GCP_PROJECT_ID=your-project-id

# Optional
export GOOGLE_CLOUD_LOCATION=us-central1
```

## 📊 Workflow Tracking

Every workflow gets an ID:
```
workflow_20251216_103000
```

Use it to track progress:
```
> Show workflow status for workflow_20251216_103000
```

## 🔐 Safety

✅ SQL is **always** shown before execution  
✅ User **must** approve before executing  
✅ All operations are **tracked**  
✅ State is **preserved** in session  

## 📦 Project Structure

```
agents/
├── orchestration/          # Main coordinator
├── staging_loader_agent/   # Stage 1
├── schema_mapping/         # Stage 2
├── validation/             # Stage 3
└── etl_agent/             # Stage 4
```

## 🧪 Testing

```bash
# Test complete integration
python agents/orchestration/test_etl_integration.py

# Test individual agents
adk run agents/[agent_name]
```

## 📚 Documentation

- [Complete Workflow Guide](agents/orchestration/COMPLETE_WORKFLOW_GUIDE.md)
- [ETL Agent README](agents/etl_agent/README.md)
- [Integration Summary](INTEGRATION_COMPLETE.md)

## 🎯 Example Workflows

### World Bank Data
```
1. Load worldbank CSVs to staging
2. Map staging to target (star schema)
3. Validate data quality
4. Generate and execute ETL SQL
5. Ready for analytics!
```

### Commercial Lending
```
1. Load loan/borrower/collateral data
2. Map to dimensional model
3. Validate referential integrity
4. Execute ETL to data warehouse
5. Business intelligence ready!
```

## ⚡ Tips

- Use **FIX mode** for comprehensive mappings
- Use **REPORT mode** for validation
- Always **review SQL** before executing
- **Track workflows** with IDs
- **Test with small datasets** first

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "GCP_PROJECT_ID not set" | `export GCP_PROJECT_ID=your-project-id` |
| "Mapping not found" | `> List all mappings` |
| "Table not found" | Ensure staging data is loaded |
| "Validation failed" | Review results, fix data, retry |
| "SQL execution failed" | Review SQL, check schemas, test single table |

## 🎉 Summary

**4 Stages** → **Complete Pipeline** → **Production Ready**

```
Load → Map → Validate → ETL = 🎯 Data Integration!
```

---

**Quick Help**: `adk run agents/orchestration` then ask questions!

