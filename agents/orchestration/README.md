# Orchestration Agent

The Orchestration Agent coordinates multiple specialized AI agents to execute end-to-end data integration workflows.

## What It Does

Acts as a single point of contact for complex, multi-step data integration tasks:

- **Coordinates Multiple Agents**: Manages schema mapping, validation, and future agents
- **Tracks Workflows**: Maintains state across multiple steps
- **Simplifies Complexity**: Users interact with one agent instead of many
- **Provides Context**: Remembers what's been done and what's next

## Quick Start

### Run the Agent

```bash
adk run agents/orchestration
```

Then chat:
```
> Run a complete workflow from worldbank_staging_dataset to worldbank_target_dataset

[Orchestrator executes]:
1. Schema Mapping Agent: Generates mapping
2. Validation Agent: Validates data
3. Returns comprehensive results

> Show me the workflow status
[Displays complete workflow history and results]
```

### Test Locally

```bash
cd agents/orchestration
python test_local.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Orchestration Agent                         │
│         (Single Point of Contact for Users)                  │
└──────────────────┬───────────────────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌──────────────────┐
│ Schema Mapping  │  │ Validation Agent │
│     Agent       │  │                  │
│                 │  │                  │
│ • Generate maps │  │ • Validate data  │
│ • Analyze       │  │ • Check quality  │
│   schemas       │  │ • Log errors     │
└─────────────────┘  └──────────────────┘

         Future Agents
         ┌────────────┐
         │ ETL Agent  │
         │ Transform  │
         │ Load Agent │
         └────────────┘
```

## Integrated Agents

### 1. Schema Mapping Agent
- **Purpose**: Generate intelligent schema mappings
- **Tools**: `generate_schema_mapping()`, `get_mapping()`, `list_mappings()`
- **Output**: Schema mapping JSON with column mappings and validation rules

### 2. Validation Agent
- **Purpose**: Validate data quality
- **Tools**: `validate_data()`, `get_validation_results()`
- **Output**: Validation results with error counts and details

### 3. Future Agents (Extensible)
- **ETL Agent**: Generate transformation SQL
- **Load Agent**: Load data to target systems
- **Monitoring Agent**: Track data quality over time
- **Lineage Agent**: Track data lineage

## Capabilities

### Core Tools

**Schema Mapping:**
- `generate_schema_mapping(source_dataset, target_dataset, mode, workflow_id)`
- `get_mapping(mapping_id)`
- `list_mappings()`

**Data Validation:**
- `validate_data(mapping_id, mode, workflow_id)`
- `get_validation_results(validation_id)`

**Workflow Management:**
- `run_complete_workflow(source_dataset, target_dataset, validation_mode)`
- `get_workflow_status(workflow_id)`
- `list_workflows()`

## Usage Patterns

### Pattern 1: Complete End-to-End Workflow

**Use Case**: Run everything at once

```
User: Process data from staging to production

Agent: I'll run the complete workflow:
       1. Generate schema mapping
       2. Validate the data
       
       [Executes both steps]
       
       Results:
       - Mapped 5 tables with 42 columns
       - Found 3 data quality issues
       
       Next: Review errors in staging_errors table
```

### Pattern 2: Step-by-Step with Review

**Use Case**: More control over each step

```
User: Map worldbank_staging to worldbank_target

Agent: [Generates schema mapping]
       Created mapping for 5 tables. 
       Would you like to proceed with validation?

User: Yes, validate it

Agent: [Runs validation]
       Validated 5 tables, found 3 errors.
       Details in run_id: abc-123
```

### Pattern 3: Status and History Tracking

**Use Case**: Track progress and review history

```
User: What workflows have I run?

Agent: You have 2 workflows:
       1. workflow_20251216_143000 (completed, 0 errors)
       2. workflow_20251216_150000 (completed, 3 errors)

User: Show details of the second one

Agent: [Displays complete workflow history with results]
```

### Pattern 4: Retrieve Previous Results

**Use Case**: Access past mappings and validations

```
User: List my mappings

Agent: You have 2 mappings:
       1. worldbank_staging_to_worldbank_target_fix
       2. test_staging_to_test_target_report

User: Get the worldbank mapping

Agent: [Returns complete mapping JSON]
```

## Workflow State Management

The orchestrator maintains state for:

**Workflows**: Complete end-to-end executions
```python
{
  "workflow_id": "workflow_20251216_143000",
  "created_at": "2025-12-16T14:30:00",
  "steps": [
    {"step": "schema_mapping", "status": "completed", ...},
    {"step": "data_validation", "status": "completed", ...}
  ]
}
```

**Schema Mappings**: Generated mappings
```python
{
  "mapping_id": "worldbank_staging_to_worldbank_target_fix",
  "mapping": { ... full mapping data ... }
}
```

**Validation Results**: Validation run results
```python
{
  "validation_id": "worldbank_validation_20251216143500",
  "results": { ... full validation results ... }
}
```

## Example Workflows

### Example 1: Quick Data Integration

```
User: I need to integrate worldbank staging data to target

Orchestrator:
  Step 1: Calling Schema Mapping Agent
  ✓ Generated mapping for 5 tables
  
  Step 2: Calling Validation Agent
  ✓ Validated 5 tables
  ✗ Found 3 data quality issues
  
  Summary:
  - Tables mapped: 5
  - Tables validated: 5
  - Errors found: 3
  
  Next steps:
  1. Review errors in staging_errors table
  2. Fix data quality issues
  3. Re-run validation
```

### Example 2: Iterative Development

```
Session 1:
User: Map staging to target in REPORT mode
Orchestrator: [Generates, finds 10 unmapped columns]

User: Now generate in FIX mode
Orchestrator: [Generates with defaults]

User: Validate using the FIX mapping
Orchestrator: [Validates, finds 2 errors]

Session 2:
User: List my workflows
Orchestrator: [Shows history from session 1]

User: Re-run validation after fixing data
Orchestrator: [Validates again, 0 errors]
```

### Example 3: Multiple Dataset Processing

```
User: Process these datasets:
      - worldbank_staging → worldbank_target
      - lending_staging → lending_target

Orchestrator:
  Workflow 1: worldbank
    ✓ Mapping generated
    ✓ Validation completed (0 errors)
  
  Workflow 2: lending
    ✓ Mapping generated
    ✓ Validation completed (5 errors)
  
  Summary: 2 workflows completed
  Next: Review lending errors
```

## Configuration

### Environment Variables

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

### Dependencies

Ensure all agent dependencies are installed:

```bash
# Orchestration agent
pip install -r requirements.txt

# Schema mapping agent
pip install -r ../schema_mapping/requirements.txt

# Validation agent  
pip install -r ../validation/requirements.txt
```

## Extending the Orchestrator

### Adding New Agents

To integrate a new agent (e.g., ETL Agent):

1. **Create the agent tool**:

```python
def generate_etl_sql(mapping_id: str, workflow_id: str = None) -> str:
    """Generate ETL SQL from a schema mapping."""
    # Import the ETL agent
    from agents.etl.etl_generator import generate_sql
    
    # Get mapping from orchestrator's memory
    if mapping_id not in _schema_mappings:
        return json.dumps({"status": "error", "message": "Mapping not found"})
    
    # Call the ETL agent
    result = generate_sql(_schema_mappings[mapping_id])
    
    # Update workflow state
    # ... track this step
    
    return json.dumps(result)
```

2. **Add tool to agent**:

```python
root_agent = Agent(
    ...
    tools=[
        # Existing tools
        generate_schema_mapping,
        validate_data,
        run_complete_workflow,
        # New tool
        generate_etl_sql,  # <-- Add here
        ...
    ]
)
```

3. **Update instructions**:

Update the agent's instruction string to mention the new capability.

### Creating New Workflows

Add custom workflows by creating new tool functions:

```python
def run_custom_workflow(params) -> str:
    """Execute a custom multi-step workflow."""
    # Step 1: Schema mapping
    mapping_result = generate_schema_mapping(...)
    
    # Step 2: Validation
    validation_result = validate_data(...)
    
    # Step 3: Your custom step
    custom_result = your_custom_function(...)
    
    # Return combined results
    return json.dumps({...})
```

## Benefits

### For End Users

- **Simplified Interface**: One agent instead of many
- **Guided Workflows**: Agent knows what to do next
- **Context Preservation**: Remembers past operations
- **Natural Language**: No need to learn multiple interfaces

### For Developers

- **Modularity**: Each agent focuses on one thing
- **Extensibility**: Easy to add new agents
- **Reusability**: Agents can be called independently
- **Maintainability**: Changes to one agent don't affect others

### For Operations

- **Workflow Tracking**: Complete audit trail
- **Error Handling**: Centralized error management
- **Coordination**: Handles agent dependencies
- **Observability**: Single point for monitoring

## Troubleshooting

### Issue: "Agent not found"

**Solution**: Ensure the agent path is in sys.path:

```python
import sys
sys.path.insert(0, "/path/to/agents")
```

### Issue: "Mapping not found"

**Solution**: Generate a mapping first:

```
User: Validate data
Agent: No mapping found. Generate one first with:
       generate_schema_mapping()
```

### Issue: "Workflow incomplete"

**Solution**: Check workflow status:

```
User: Get workflow status for workflow_123
Agent: [Shows which steps completed and which failed]
```

## Files

- `agent.py` - Main orchestration agent
- `__init__.py` - Package exports
- `requirements.txt` - Dependencies
- `test_local.py` - Local testing
- `README.md` - This file

## Future Enhancements

Planned features:

- ✅ Schema mapping coordination
- ✅ Validation coordination
- ✅ Workflow state tracking
- ⏳ ETL SQL generation
- ⏳ Data transformation execution
- ⏳ Multi-dataset batch processing
- ⏳ Workflow templates
- ⏳ Scheduled workflows
- ⏳ Notification integration

## Resources

- [Agent Development Kit (ADK) Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-builder)
- [Schema Mapping Agent](../schema_mapping/README.md)
- [Validation Agent](../validation/VALIDATOR_README.md)

## Support

For issues or questions:
1. Check this README
2. Run `test_local.py` for diagnostics
3. Review agent logs
4. Verify environment variables

---

**Version**: 1.0
**Last Updated**: December 16, 2025
**Status**: Production Ready

