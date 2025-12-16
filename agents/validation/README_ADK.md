# Validation Agent - ADK Integration

The Validation Agent is now compatible with Google Agent Development Kit (ADK) for interactive use.

## Quick Start with ADK

### 1. Run with ADK CLI

```bash
# Interactive mode
adk run agents/validation

# Or from within the directory
cd agents/validation
adk run .
```

### 2. Test Locally

```bash
cd agents/validation
python test_local.py
```

## What It Does

Validates BigQuery staging data quality using:
- **Schema Mapping Rules**: From Schema Mapping Agent
- **LLM-Generated SQL**: Gemini 2.5 Flash creates validation queries
- **Automated Checks**: UNIQUENESS, NOT_NULL, TYPE_CONVERSION, RANGE, NUMERIC
- **Error Logging**: All errors logged to `staging_errors` table

## Usage Examples

### Example 1: Validate with Schema Mapping

```
User: I have a schema mapping JSON. Can you validate my data?

Agent: Yes! Please provide:
       1. The schema mapping JSON (or file path)
       2. The source dataset name (if not in mapping)
       3. Mode: REPORT (log errors) or FIX (attempt corrections)

User: [Provides mapping JSON]

Agent: [Validates data]
       ✓ Validated 5 tables
       ✗ Found 12 data quality issues
       
       Breakdown:
       - UNIQUENESS: 2 duplicates
       - NOT_NULL: 3 NULL values
       - RANGE: 7 out-of-range values
       
       Run ID: abc-123
       Query: SELECT * FROM staging_errors WHERE run_id = 'abc-123'
```

### Example 2: Review Past Validations

```
User: What validations have I run?

Agent: [Calls list_validations]
       You have 2 validation runs:
       1. validation_20251216143000 (5 tables, 12 errors)
       2. validation_20251216150000 (5 tables, 0 errors)

User: Show me details of the first one

Agent: [Calls get_validation_results]
       [Displays complete results]
```

## Agent Capabilities

### 1. `validate_schema_mapping(schema_mapping_json, source_dataset, mode)`

Validates data using schema mapping rules.

**Parameters:**
- `schema_mapping_json`: Schema mapping JSON string or file path
- `source_dataset`: Source dataset name (auto-detected if not provided)
- `mode`: "REPORT" or "FIX" (default: REPORT)

**Returns:** JSON with validation results including run_id

### 2. `get_validation_results(validation_id)`

Retrieve stored validation results.

**Parameters:**
- `validation_id`: The validation ID to retrieve

**Returns:** JSON with complete validation results

### 3. `list_validations()`

List all validation runs in the session.

**Returns:** JSON with list of validations

## Validation Types

### UNIQUENESS Checks
- Detects duplicate rows based on primary keys
- Identifies composite key violations
- Flags uniqueness constraint violations

### NOT_NULL Checks
- Finds NULL values in required fields
- Based on target schema REQUIRED mode
- Critical for data integrity

### TYPE_CONVERSION Checks
- Validates data can be converted to target types
- Example: STRING values that can't convert to INT64
- Uses SAFE_CAST to detect issues

### RANGE Checks
- Validates values within expected ranges
- Example: Year between 1900-2100
- Example: Percentage between 0-100

### NUMERIC Checks
- Ensures numeric columns contain valid numbers
- Detects non-numeric values in numeric fields
- Uses SAFE_CAST to FLOAT64

## Output Format

```json
{
  "status": "success",
  "validation_id": "validation_20251216143000",
  "run_id": "abc-123-def-456",
  "source_dataset": "worldbank_staging_dataset",
  "mode": "REPORT",
  "summary": {
    "tables_validated": 5,
    "total_validations": 15,
    "total_errors": 12,
    "errors_table": "project.dataset.staging_errors"
  },
  "tables": [
    {
      "source_table": "project.dataset.staging_countries",
      "target_table": "project.dataset.dim_country",
      "total_errors": 3,
      "validations_run": 3
    }
  ],
  "query_to_see_errors": "SELECT * FROM `project.dataset.staging_errors` WHERE run_id = 'abc-123' ORDER BY created_at DESC"
}
```

## Integration with Orchestration Agent

The Validation Agent works seamlessly with the Orchestration Agent:

```
User: Run complete workflow from worldbank_staging to worldbank_target

Orchestration Agent:
  Step 1: [Calls Schema Mapping Agent]
  Step 2: [Calls Validation Agent] ← Uses this agent
  
  Results: 5 tables validated, 3 errors found
```

## Environment Variables

Uses consistent environment variables:

```bash
# Required
GCP_PROJECT_ID=your-project-id
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=1
```

## Files

- `agent.py` - ADK agent definition (NEW)
- `test_local.py` - Local testing script (NEW)
- `__init__.py` - Package exports (UPDATED)
- `data_validator.py` - Core validation logic (UNCHANGED)
- `api.py` - Flask API (UNCHANGED)
- `requirements.txt` - Dependencies (UPDATED)
- `README_ADK.md` - This file (NEW)

## Backward Compatibility

All original functionality preserved:

**Original CLI:**
```bash
python run_data_validator.py mapping.json worldbank_staging_dataset REPORT
```

**Original API:**
```bash
python api.py
# POST to /validate
```

**Original Function Import:**
```python
from agents.validation.data_validator import validate_schema_mapping
result = validate_schema_mapping(mapping_json, source_dataset, mode)
```

## Workflow Example

### Complete Validation Workflow

```
1. User: Run validation

2. Agent: I need a schema mapping. You can:
   - Provide existing mapping JSON
   - Generate one with Schema Mapping Agent
   
3. User: [Provides/generates mapping]

4. Agent: [Validates data]
   
5. Results:
   ✓ 5 tables validated
   ✗ 12 errors found
   
   Error Breakdown:
   - dim_country: 3 errors
   - dim_indicator: 2 errors
   - fact_indicator_values: 7 errors
   
6. Agent: To view errors:
   SELECT * FROM staging_errors WHERE run_id = 'abc-123'
   
   Next steps:
   1. Fix NULL values in country_code
   2. Remove duplicate rows
   3. Correct out-of-range years
   4. Re-run validation
```

## Troubleshooting

### Issue: "Dataset not found"

```bash
# Verify dataset exists
bq ls PROJECT:DATASET
```

### Issue: "Permission denied"

```bash
# Re-authenticate
gcloud auth application-default login
```

### Issue: "No validation queries generated"

- Check schema mapping format
- Verify validation rules exist
- Ensure LLM connection works

### Issue: "Schema mapping required"

- Generate mapping first with Schema Mapping Agent
- Or provide existing mapping JSON

## Best Practices

1. **Always use schema mappings** - Don't try to validate without proper mappings
2. **Start with REPORT mode** - Understand issues before attempting fixes
3. **Review errors systematically** - Query staging_errors table for details
4. **Fix in batches** - Address similar errors together
5. **Re-validate after fixes** - Ensure errors are resolved

## Next Steps

After validation:

1. **Query errors**: Use run_id to see detailed errors
2. **Analyze patterns**: Group errors by type and table
3. **Fix data**: Update source data or ETL logic
4. **Re-validate**: Run validation again
5. **Proceed**: When errors = 0, proceed with ETL

## Resources

- [Main Validation README](VALIDATOR_README.md)
- [Orchestration Agent](../orchestration/README.md)
- [Schema Mapping Agent](../schema_mapping/README.md)

## Support

Need help?
1. Run `test_local.py` for diagnostics
2. Check environment variables
3. Verify BigQuery permissions
4. Review agent logs

---

**Version**: 1.0 (ADK Compatible)
**Last Updated**: December 16, 2025
**Model**: Gemini 2.5 Flash
**Status**: ✅ Production Ready

