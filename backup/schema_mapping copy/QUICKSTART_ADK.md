# Schema Mapping Agent - Quick Start with ADK

Get started with the Schema Mapping Agent using Google's Agent Development Kit (ADK) in 5 minutes!

## Prerequisites

1. **Google Cloud Project** with:
   - BigQuery API enabled
   - Vertex AI API enabled
   - Datasets to map (source and target)

2. **Authentication**:
   ```bash
   gcloud auth application-default login
   ```

3. **Environment Variables** (create `.env` file):
   ```bash
   GCP_PROJECT_ID=your-project-id
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   GOOGLE_GENAI_USE_VERTEXAI=1
   ```

4. **Dependencies** (if not already installed):
   ```bash
   pip install google-adk google-cloud-bigquery vertexai python-dotenv
   ```

## Option 1: Run with ADK (Interactive)

### Step 1: Start the Agent

From the project root:

```bash
adk run agents/schema_mapping
```

Or from the agent directory:

```bash
cd agents/schema_mapping
adk run .
```

### Step 2: Chat with the Agent

The ADK will start an interactive session. Try these commands:

**Example 1: Get Help**
```
> Hello! What can you help me with?
```

**Example 2: Fetch a Table Schema**
```
> Get the schema for table ccibt-hack25ww7-750.worldbank_staging_dataset.staging_countries
```

**Example 3: Generate Mapping (REPORT Mode)**
```
> Generate a schema mapping between worldbank_staging_dataset and worldbank_target_dataset in REPORT mode
```

**Example 4: Generate Mapping (FIX Mode)**
```
> Create a mapping from worldbank_staging_dataset to worldbank_target_dataset in FIX mode
```

### Step 3: Review Results

The agent will:
- ✅ Fetch schemas from BigQuery
- ✅ Use Gemini to intelligently match tables/columns
- ✅ Generate validation rules
- ✅ Return comprehensive JSON mapping
- ✅ Explain results in natural language

## Option 2: Test Locally (Programmatic)

### Step 1: Run Test Script

```bash
cd agents/schema_mapping
python test_local.py
```

This will:
- Run predefined test queries
- Display agent responses
- Show tool calls and results
- Verify everything works

### Step 2: Review Output

You'll see:
```
TESTING SCHEMA MAPPING AGENT LOCALLY
=====================================

Running test queries:
  1. Hello! What can you do?
  2. Can you fetch the schema for...
  3. Generate a schema mapping...

✅ Test completed successfully!
Total events generated: X

Conversation Summary:
-----------------------------------
[USER] Hello! What can you do?
[AGENT] I can help you with schema mapping...
...
```

## Option 3: Original CLI (Non-Interactive)

If you prefer the original command-line interface:

```bash
python run_schema_mapper.py \
    --source worldbank_staging_dataset \
    --target worldbank_target_dataset \
    --output mapping.json \
    --mode FIX
```

This saves results directly to a JSON file without conversation.

## Understanding the Output

### REPORT Mode Output

```json
{
  "status": "success",
  "mapping": {
    "metadata": {
      "mode": "REPORT",
      "confidence": "high"
    },
    "mappings": [
      {
        "source_table": "staging.countries",
        "target_table": "target.dim_country",
        "column_mappings": [
          {
            "source_column": "UNMAPPED",
            "target_column": "loaded_at",
            "source_type": "MISSING",
            "notes": "No source column found"
          }
        ],
        "mapping_errors": [
          {
            "error_type": "UNMAPPED_TARGET_COLUMN",
            "target_column": "loaded_at",
            "severity": "WARNING"
          }
        ]
      }
    ]
  }
}
```

**Use REPORT mode when:**
- You want to see what's missing
- Manual review is needed
- Understanding gaps in source data

### FIX Mode Output

```json
{
  "status": "success",
  "mapping": {
    "metadata": {
      "mode": "FIX",
      "confidence": "high"
    },
    "mappings": [
      {
        "column_mappings": [
          {
            "source_column": "GENERATED",
            "target_column": "loaded_at",
            "source_type": "EXPRESSION",
            "transformation": "DEFAULT: CURRENT_TIMESTAMP()",
            "notes": "Auto-generated timestamp"
          }
        ]
      }
    ]
  }
}
```

**Use FIX mode when:**
- You want automatic default suggestions
- Building ETL pipelines
- Need SQL expressions for missing columns

## Common Use Cases

### Use Case 1: Initial Schema Analysis

```
User: Show me all tables in worldbank_staging_dataset
Agent: [Calls fetch_dataset_schemas and displays tables]

User: Now show me the target dataset
Agent: [Displays target tables]

User: Generate a mapping in REPORT mode
Agent: [Creates mapping and explains gaps]
```

### Use Case 2: ETL Pipeline Setup

```
User: Generate a mapping from worldbank_staging_dataset to worldbank_target_dataset in FIX mode
Agent: [Creates mapping with default values]

User: Save this mapping
Agent: [Returns JSON that you can save to file]
```

### Use Case 3: Data Quality Review

```
User: What validation rules would you suggest for the mapping?
Agent: [Explains validation rules from the mapping]

User: Show me unmapped columns
Agent: [Lists columns that need attention]
```

## Troubleshooting

### Issue: "Module not found"

```bash
# Install dependencies
pip install -r requirements.txt
```

### Issue: "Permission denied" (BigQuery)

```bash
# Re-authenticate
gcloud auth application-default login

# Verify project
gcloud config get-value project
```

### Issue: "Vertex AI not initialized"

Check your `.env` file has:
```bash
GCP_PROJECT_ID=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=1
```

### Issue: "Dataset not found"

Verify dataset exists:
```bash
bq ls
bq ls your-project:your_dataset
```

## Next Steps

After generating a mapping:

1. **Review the JSON**: Check accuracy of table/column matches
2. **Validate Rules**: Verify validation rules match requirements
3. **Test with Data**: Use validation agent to check data quality
4. **Build ETL**: Use mappings to create transformation SQL
5. **Iterate**: Refine mappings based on results

## Advanced Usage

### Custom Prompts

Modify the agent's behavior by editing `agent.py`:

```python
root_agent = Agent(
    model='gemini-2.5-flash',
    instruction='Your custom instructions here...',
    tools=[...],
)
```

### Integration with Other Agents

Chain with validation agent:

```python
# 1. Generate mapping
mapping = schema_mapping_agent.generate_mapping(...)

# 2. Use mapping for validation
validation_agent.validate_data(table, mapping['validation_rules'], 'REPORT')
```

### Programmatic Access

Use the agent in your Python code:

```python
from agents.schema_mapping import root_agent
from google.adk.runners import InMemoryRunner

runner = InMemoryRunner(agent=root_agent)
events = await runner.run_debug(
    user_messages=["Generate mapping between X and Y"],
    user_id="my_user",
    session_id="my_session"
)
```

## Resources

- **Main README**: `README.md` - Full documentation
- **ADK Guide**: `README_ADK.md` - Detailed ADK integration
- **API Guide**: `API_README.md` - REST API documentation
- **Summary**: `SUMMARY.md` - Feature overview

## Support

Need help?
1. Check the README files
2. Run `test_local.py` for diagnostics
3. Review agent logs for errors
4. Verify environment variables and permissions

---

**Happy Mapping! 🚀**

