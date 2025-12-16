# Schema Mapping Agent - ADK Integration

This agent is now compatible with Google Agent Development Kit (ADK) for interactive use.

## Quick Start with ADK

### 1. Run with ADK CLI

From the project root:

```bash
# Interactive mode
adk run agents/schema_mapping

# Or from within the directory
cd agents/schema_mapping
adk run .
```

This will start an interactive session where you can chat with the agent.

### 2. Test Locally

```bash
cd agents/schema_mapping
python test_local.py
```

This runs predefined test queries to verify the agent works correctly.

## Usage Examples

Once you start the agent with `adk run`, you can interact with it:

### Example 1: Fetch a Single Table Schema

```
User: Get the schema for table ccibt-hack25ww7-750.worldbank_staging_dataset.staging_countries
```

The agent will call `fetch_table_schema()` and return column details.

### Example 2: Fetch All Tables in a Dataset

```
User: Show me all table schemas in worldbank_staging_dataset
```

The agent will call `fetch_dataset_schemas()` and display all tables.

### Example 3: Generate Schema Mapping (REPORT Mode)

```
User: Generate a schema mapping between worldbank_staging_dataset and worldbank_target_dataset in REPORT mode
```

This will:
- Fetch schemas from both datasets
- Use LLM to intelligently match tables and columns
- Flag unmapped columns as errors
- Generate validation rules
- Return comprehensive mapping JSON

### Example 4: Generate Schema Mapping (FIX Mode)

```
User: Create a mapping from worldbank_staging_dataset to worldbank_target_dataset in FIX mode
```

This will:
- Generate intelligent mappings
- Suggest default values for unmapped columns
- Provide SQL expressions for generated fields
- Include validation rules

## Agent Capabilities

The agent has three main tools:

### 1. `fetch_table_schema(full_table_id: str)`

Fetches detailed schema for a specific BigQuery table.

**Parameters:**
- `full_table_id`: Format "project.dataset.table"

**Returns:** JSON with table metadata and columns

### 2. `fetch_dataset_schemas(dataset_id: str)`

Fetches all table schemas from a BigQuery dataset.

**Parameters:**
- `dataset_id`: Format "project.dataset" or just "dataset"

**Returns:** JSON mapping table names to schemas

### 3. `generate_schema_mapping(source_dataset, target_dataset, mode)`

Generates comprehensive schema mapping using LLM.

**Parameters:**
- `source_dataset`: Source BigQuery dataset name
- `target_dataset`: Target BigQuery dataset name
- `mode`: "REPORT" or "FIX"

**Returns:** JSON with complete schema mapping

## Environment Variables

Ensure these are set (in `.env` or environment):

```bash
# Required
GCP_PROJECT_ID=your-project-id
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=1

# Optional
ADK_WEB_HOST=127.0.0.1
ADK_WEB_PORT=8000
```

## Configuration

The agent is configured in `agent.py`:

- **Model**: `gemini-2.5-flash`
- **Name**: `schema_mapping_agent`
- **Tools**: 3 functions for schema analysis and mapping

## Modes: REPORT vs FIX

### REPORT Mode

- Flags unmapped columns as `"UNMAPPED"`
- Creates error reports in `mapping_errors` array
- Use for: Review and manual intervention

### FIX Mode

- Suggests intelligent defaults for unmapped columns
- Uses `"GENERATED"` + `"EXPRESSION"` pattern
- Provides SQL transformations with `"DEFAULT:"` prefix
- Use for: Automatic default value generation

## Output Format

The agent returns structured JSON:

```json
{
  "status": "success",
  "mapping": {
    "metadata": {
      "source_dataset": "...",
      "target_dataset": "...",
      "mode": "FIX",
      "confidence": "high"
    },
    "mappings": [
      {
        "source_table": "...",
        "target_table": "...",
        "column_mappings": [...],
        "validation_rules": [...],
        "primary_key": [...],
        "unmapped_target_columns": [...]
      }
    ]
  },
  "summary": {
    "num_mappings": 5,
    "confidence": "high"
  }
}
```

## Integration with Existing Scripts

The agent still supports the original CLI and API interfaces:

### Original CLI

```bash
python run_schema_mapper.py \
    --source worldbank_staging_dataset \
    --target worldbank_target_dataset \
    --output mapping.json \
    --mode FIX
```

### FastAPI

```bash
python api.py
# Then POST to http://localhost:8080/generate-mapping
```

## Troubleshooting

### Error: "Module not found"

Ensure you're running from the correct directory and dependencies are installed:

```bash
pip install -r requirements.txt
```

### Error: "BigQuery permission denied"

Authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

### Error: "Vertex AI not initialized"

Check environment variables:

```bash
echo $GCP_PROJECT_ID
echo $GOOGLE_CLOUD_LOCATION
```

## Development

### File Structure

```
agents/schema_mapping/
├── agent.py              # ADK agent definition (NEW)
├── test_local.py         # Local testing script (NEW)
├── schema_mapper.py      # Original core logic
├── run_schema_mapper.py  # CLI interface
├── api.py               # FastAPI wrapper
├── requirements.txt     # Dependencies
└── README_ADK.md        # This file (NEW)
```

### Testing Changes

```bash
# Test with ADK runner
python test_local.py

# Test with original CLI
python run_schema_mapper.py --source staging --target target --mode FIX

# Test API
python api.py
```

## Next Steps

After running the agent:

1. **Review Mappings**: Check the generated JSON for accuracy
2. **Validate Rules**: Verify validation rules match business requirements
3. **Use in ETL**: Apply mappings to data transformation pipelines
4. **Iterate**: Refine mappings based on data quality results

## Resources

- [Google ADK Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-builder)
- [BigQuery Schema Documentation](https://cloud.google.com/bigquery/docs/schemas)
- [Gemini API Reference](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference)

## Support

For issues:
1. Check environment variables
2. Verify BigQuery permissions
3. Review agent logs for detailed error messages
4. Test with `test_local.py` for debugging

