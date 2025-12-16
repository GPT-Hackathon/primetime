# Orchestration Agent - Quick Start

Get started with the Orchestration Agent in 2 minutes!

## What Is This?

A single AI agent that coordinates multiple specialized agents to run complete data integration workflows. Think of it as your data integration assistant that knows how to use all the tools.

## Run It Now

### Step 1: Start the Agent

```bash
adk run agents/orchestration
```

### Step 2: Try These Commands

**Complete workflow (easiest):**
```
> Run a complete workflow from worldbank_staging_dataset to worldbank_target_dataset
```

This will:
1. Generate schema mapping
2. Validate the data
3. Return comprehensive results

**Step-by-step workflow:**
```
> Generate schema mapping from worldbank_staging_dataset to worldbank_target_dataset in FIX mode

> Now validate the data using that mapping

> Show me the workflow status
```

**Check what you've done:**
```
> List my workflows

> List my mappings

> Get workflow status for workflow_[ID]
```

## What Happens Behind the Scenes

When you say: *"Run a complete workflow from staging to target"*

The orchestrator:
1. 📋 Calls **Schema Mapping Agent** to generate mappings
2. ✅ Calls **Validation Agent** to check data quality
3. 📊 Returns combined results
4. 🎯 Suggests next steps

You don't need to know which agent does what - the orchestrator handles it!

## Common Use Cases

### Use Case 1: Quick Data Integration Check

```
User: I need to check if worldbank staging data is ready for loading

Orchestrator: 
  [Generates schema mapping]
  [Validates data]
  
  Results:
  ✓ 5 tables mapped
  ✗ Found 3 data quality issues
  
  Issues:
  - country_code: 2 NULL values
  - year: 1 value out of range
  
  Next: Fix these 3 issues and re-validate
```

### Use Case 2: Compare Datasets

```
User: What datasets have I processed?

Orchestrator:
  You have 2 workflows:
  1. worldbank (completed, 0 errors) ✓
  2. lending (completed, 5 errors) ✗
  
  Would you like details on either?
```

### Use Case 3: Track Progress

```
User: Show status of workflow_20251216_143000

Orchestrator:
  Workflow Status:
  ✓ Step 1: Schema mapping completed
    - 5 tables mapped
    - Confidence: HIGH
  
  ✓ Step 2: Validation completed
    - 5 tables validated
    - 3 errors found
    
  Status: COMPLETED
  Run ID: abc-123 (for querying staging_errors)
```

## Key Features

### 1. Multi-Agent Coordination

You interact with ONE agent that coordinates multiple specialized agents:
- Schema Mapping Agent
- Validation Agent
- Future agents (ETL, Transform, etc.)

### 2. Workflow State

The orchestrator remembers:
- ✅ What mappings you've generated
- ✅ What validations you've run
- ✅ Complete workflow history

### 3. Smart Guidance

The agent:
- 🎯 Suggests what to do next
- 💡 Explains results in business terms
- 🔧 Guides you through fixes
- 📊 Shows progress tracking

## Quick Reference

### Generate Mapping

```
> Generate schema mapping from [source] to [target] in [FIX/REPORT] mode
```

### Validate Data

```
> Validate data using mapping [mapping_id]
```

### Run Complete Workflow

```
> Run complete workflow from [source] to [target]
```

### Check Status

```
> List workflows
> List mappings
> Get workflow status for [workflow_id]
> Get mapping [mapping_id]
```

## What You Get

**After a workflow completes, you get:**

1. **Workflow ID**: Track this workflow
2. **Mapping ID**: Reference the schema mapping
3. **Validation Run ID**: Query errors in BigQuery
4. **Summary**: Tables processed, errors found
5. **Next Steps**: What to do next

**Example output:**
```json
{
  "workflow_id": "workflow_20251216_143000",
  "summary": {
    "tables_mapped": 5,
    "tables_validated": 5,
    "errors_found": 3
  },
  "next_steps": [
    "Review errors in staging_errors table",
    "Fix data quality issues",
    "Re-run validation"
  ]
}
```

## Tips

1. **Start with complete workflow** - Easiest way to get started
2. **Use FIX mode** - Generates complete mappings with defaults
3. **Track workflow IDs** - Easy to reference later
4. **Ask for status** - See complete history anytime
5. **Natural language** - Just describe what you want

## Example Session

```
User: Hi! What can you do?

Agent: I orchestrate data integration workflows! I can:
       - Generate schema mappings
       - Validate data quality
       - Run complete end-to-end workflows
       - Track progress and history
       
       Try: "Run complete workflow from X to Y"

User: Run complete workflow from worldbank_staging_dataset to worldbank_target_dataset

Agent: Starting workflow...
       
       Step 1: Generating schema mapping ✓
       - Mapped 5 tables with 42 columns
       
       Step 2: Validating data ✓
       - Validated 5 tables
       - Found 3 data quality issues
       
       Workflow complete!
       Workflow ID: workflow_20251216_143000
       
       Next steps:
       1. Review errors (run_id: abc-123)
       2. Fix 3 data quality issues
       3. Re-run validation

User: What were the errors?

Agent: Found 3 errors:
       1. country_code: 2 NULL values
       2. year: 1 value out of range (2150)
       3. population: 1 invalid numeric value
       
       Check staging_errors table:
       SELECT * FROM staging_errors WHERE run_id = 'abc-123'

User: Thanks! I'll fix those and re-run

Agent: Great! When you're ready:
       "Run validation using mapping worldbank_staging_to_worldbank_target_fix"
```

## Troubleshooting

**Issue: "No mappings found"**
→ Generate a mapping first

**Issue: "Agent import error"**
→ Ensure all dependencies installed: `pip install -r requirements.txt`

**Issue: "Validation failed"**
→ Check BigQuery permissions and dataset names

## Next Steps

1. ✅ Try the quick start above
2. 📖 Read [README.md](README.md) for complete documentation
3. 🔧 See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) to add your own agents
4. 🧪 Run `test_local.py` for automated tests

## Need Help?

Ask the agent!
```
> How do I run a complete workflow?
> What workflows have I run?
> Show me an example
> Help me understand the results
```

---

**Ready to start?**

```bash
adk run agents/orchestration

> Run complete workflow from worldbank_staging_dataset to worldbank_target_dataset
```

That's it! 🚀

