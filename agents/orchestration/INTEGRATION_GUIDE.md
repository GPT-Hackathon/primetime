# Integration Guide - Adding Your Agent to the Orchestrator

This guide shows how to integrate your agent with the Orchestration Agent so it can be part of coordinated workflows.

## Overview

The Orchestration Agent coordinates multiple specialized agents. To add your agent, you'll:

1. **Create a wrapper function** in the orchestrator
2. **Register your tool** with the orchestration agent
3. **Update the agent instructions** to mention your capability
4. **Test the integration**

## Step-by-Step Integration

### Step 1: Understand the Pattern

Look at existing integrations in `agent.py`:

```python
def generate_schema_mapping(source_dataset: str, target_dataset: str, mode: str = "FIX", workflow_id: str = None) -> str:
    """Generate schema mapping between source and target datasets."""
    try:
        # Import your agent's function
        from agents.schema_mapping.schema_mapper import generate_schema_mapping as sm_generate
        
        # Call your agent
        result = sm_generate(...)
        
        # Store results in orchestrator's memory
        _schema_mappings[mapping_id] = result["mapping"]
        
        # Update workflow state
        _workflow_state[workflow_id]["steps"].append({...})
        
        # Return formatted response
        return json.dumps({
            "status": "success",
            "workflow_id": workflow_id,
            ...
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
```

**Key points:**
- Import your agent's function
- Call it with appropriate parameters
- Store results in orchestrator's memory
- Update workflow state for tracking
- Return JSON string (not dict)
- Handle errors gracefully

### Step 2: Create Your Wrapper Function

**Example: Adding an ETL Agent**

```python
# Add to agent.py

def generate_etl_sql(mapping_id: str, output_format: str = "SQL", workflow_id: str = None) -> str:
    """
    Generate ETL SQL from a schema mapping.
    
    Delegates to the ETL Agent to create transformation SQL.

    Args:
        mapping_id: ID of the schema mapping to use
        output_format: "SQL", "DBT", or "DATAFORM"
        workflow_id: Optional workflow ID for tracking

    Returns:
        JSON string with ETL SQL generation results
    """
    try:
        # Check if mapping exists
        if mapping_id not in _schema_mappings:
            return json.dumps({
                "status": "error",
                "message": f"Mapping '{mapping_id}' not found",
                "available_mappings": list(_schema_mappings.keys())
            }, indent=2)
        
        # Import your ETL agent function
        from agents.etl.etl_generator import generate_sql
        
        print(f"🔄 Orchestrator: Calling ETL Agent...")
        print(f"   Mapping ID: {mapping_id}")
        print(f"   Output Format: {output_format}")
        
        # Get the mapping
        mapping_data = _schema_mappings[mapping_id]
        
        # Call your ETL agent
        result = generate_sql(
            mapping_json=mapping_data,
            output_format=output_format
        )
        
        if result.get("status") == "success":
            # Store ETL results
            etl_id = f"{mapping_id}_etl_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            _etl_results[etl_id] = result  # Add _etl_results dict at top
            
            # Update workflow state
            if not workflow_id:
                workflow_id = f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            if workflow_id not in _workflow_state:
                _workflow_state[workflow_id] = {
                    "created_at": datetime.utcnow().isoformat(),
                    "steps": []
                }
            
            _workflow_state[workflow_id]["steps"].append({
                "step": "etl_generation",
                "status": "completed",
                "etl_id": etl_id,
                "mapping_id": mapping_id,
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "num_sql_files": result.get("num_files", 0),
                    "output_format": output_format
                }
            })
            
            return json.dumps({
                "status": "success",
                "workflow_id": workflow_id,
                "etl_id": etl_id,
                "message": "ETL SQL generated successfully",
                "summary": {
                    "num_sql_files": result.get("num_files", 0),
                    "output_format": output_format,
                    "total_lines": result.get("total_lines", 0)
                },
                "next_steps": [
                    "Review generated SQL files",
                    "Test SQL on sample data",
                    "Deploy to production"
                ]
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": result.get("message", "ETL generation failed")
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error generating ETL SQL: {str(e)}"
        }, indent=2)
```

### Step 3: Add Storage for Your Results

At the top of `agent.py`, add a dictionary to store your agent's results:

```python
# In-memory storage for workflow state
_workflow_state = {}
_schema_mappings = {}
_validation_results = {}
_etl_results = {}  # <-- Add this for your agent
```

### Step 4: Create Retrieval Functions

Add functions to retrieve your agent's results:

```python
def get_etl_results(etl_id: str) -> str:
    """
    Retrieve ETL generation results by ID.

    Args:
        etl_id: The ETL generation ID to retrieve

    Returns:
        JSON string with ETL results
    """
    if etl_id not in _etl_results:
        return json.dumps({
            "status": "error",
            "message": f"ETL results '{etl_id}' not found",
            "available_etl": list(_etl_results.keys())
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "etl_id": etl_id,
        "results": _etl_results[etl_id]
    }, indent=2)


def list_etl_results() -> str:
    """List all ETL generation results in this session."""
    if not _etl_results:
        return json.dumps({
            "status": "success",
            "etl_results": [],
            "count": 0,
            "message": "No ETL results yet. Use generate_etl_sql() to create some."
        }, indent=2)
    
    etl_summary = []
    for etl_id, etl_data in _etl_results.items():
        etl_summary.append({
            "etl_id": etl_id,
            "mapping_id": etl_data.get("mapping_id"),
            "output_format": etl_data.get("output_format"),
            "num_files": etl_data.get("num_files", 0)
        })
    
    return json.dumps({
        "status": "success",
        "etl_results": etl_summary,
        "count": len(etl_summary)
    }, indent=2)
```

### Step 5: Register Tools with Agent

Add your tools to the agent definition:

```python
root_agent = Agent(
    model='gemini-2.5-flash',
    name='orchestration_agent',
    description='Orchestrates multiple AI agents for end-to-end data integration workflows.',
    instruction="""...""",  # Update this (see Step 6)
    tools=[
        # Existing tools
        generate_schema_mapping,
        get_mapping,
        list_mappings,
        validate_data,
        get_validation_results,
        run_complete_workflow,
        get_workflow_status,
        list_workflows,
        
        # Your new tools
        generate_etl_sql,          # <-- Add here
        get_etl_results,           # <-- Add here
        list_etl_results,          # <-- Add here
    ],
)
```

### Step 6: Update Agent Instructions

Update the instruction string to mention your agent:

```python
instruction="""You are an Orchestration Agent that coordinates multiple specialized agents...

**Your Capabilities:**

**Schema Mapping:**
- generate_schema_mapping(...): Generate schema mapping
- ...

**Data Validation:**
- validate_data(...): Validate data using a mapping
- ...

**ETL Generation:** <-- Add this section
- generate_etl_sql(mapping_id, output_format): Generate ETL SQL
- get_etl_results(etl_id): Get ETL generation results
- list_etl_results(): List all ETL results

**Workflow Management:**
- run_complete_workflow(...): Run end-to-end workflow
- ...

When a user asks to generate ETL SQL:
1. Verify they have a mapping (if not, generate one first)
2. Use generate_etl_sql() with the mapping_id
3. Explain the generated SQL files
4. Suggest next steps (test, review, deploy)

..."""
```

### Step 7: Update Complete Workflow (Optional)

If your agent should be part of the complete workflow, update `run_complete_workflow`:

```python
def run_complete_workflow(source_dataset: str, target_dataset: str, validation_mode: str = "REPORT") -> str:
    """Run complete end-to-end data integration workflow."""
    workflow_id = f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Step 1: Generate schema mapping
        mapping_result = json.loads(generate_schema_mapping(...))
        mapping_id = mapping_result.get("mapping_id")
        
        # Step 2: Validate data
        validation_result = json.loads(validate_data(...))
        
        # Step 3: Generate ETL SQL (NEW)
        etl_result = json.loads(generate_etl_sql(
            mapping_id=mapping_id,
            output_format="SQL",
            workflow_id=workflow_id
        ))
        
        # Return comprehensive results
        return json.dumps({
            "status": "success",
            "workflow_id": workflow_id,
            "steps_completed": [
                {"step": 1, "name": "schema_mapping", ...},
                {"step": 2, "name": "data_validation", ...},
                {"step": 3, "name": "etl_generation", ...},  # <-- Add
            ],
            ...
        })
```

## Complete Integration Checklist

- [ ] Create wrapper function for your agent
- [ ] Add storage dictionary for results (`_your_agent_results = {}`)
- [ ] Create retrieval functions (`get_your_results`, `list_your_results`)
- [ ] Register tools with the agent
- [ ] Update agent instructions
- [ ] Optionally update `run_complete_workflow`
- [ ] Test integration locally
- [ ] Document your agent's capabilities
- [ ] Update QUICKSTART.md with examples

## Testing Your Integration

### 1. Unit Test Your Wrapper

```python
# test_integration.py
from agent import generate_etl_sql, _schema_mappings

# Mock data
_schema_mappings["test_mapping"] = {...}

# Test
result = generate_etl_sql("test_mapping", "SQL")
print(json.loads(result))
```

### 2. Test with ADK Runner

```python
# test_local.py
test_queries = [
    "Generate schema mapping from X to Y",
    "Generate ETL SQL using that mapping",  # <-- Test your agent
    "List ETL results",
    "Get workflow status",
]
```

### 3. Interactive Testing

```bash
adk run agents/orchestration

> Generate schema mapping from worldbank_staging to worldbank_target
> Generate ETL SQL using worldbank_staging_to_worldbank_target_fix
> Show me the ETL results
```

## Best Practices

### 1. Consistent Naming

```python
# Good naming patterns
def generate_[agent_name]_[action](...)  # generate_etl_sql
def get_[agent_name]_results(...)        # get_etl_results
def list_[agent_name]_results(...)       # list_etl_results
```

### 2. Error Handling

```python
try:
    # Your agent call
    result = your_agent_function(...)
except ImportError as e:
    return json.dumps({
        "status": "error",
        "message": f"Your agent not found. Install it first: {e}"
    })
except Exception as e:
    return json.dumps({
        "status": "error",
        "message": f"Error calling your agent: {str(e)}"
    })
```

### 3. Workflow Tracking

Always update workflow state:

```python
_workflow_state[workflow_id]["steps"].append({
    "step": "your_agent_name",
    "status": "completed",
    "your_result_id": result_id,
    "timestamp": datetime.utcnow().isoformat(),
    "summary": {...}
})
```

### 4. User Guidance

Provide clear next steps:

```python
return json.dumps({
    "status": "success",
    ...
    "next_steps": [
        "Review the generated output",
        "Test with sample data",
        "Deploy to production"
    ]
})
```

## Example Integrations

### Example 1: Simple Agent (No Dependencies)

```python
def analyze_data_quality(dataset_id: str, workflow_id: str = None) -> str:
    """Analyze data quality metrics."""
    from agents.quality.analyzer import analyze
    
    result = analyze(dataset_id)
    
    # Store and track
    analysis_id = f"quality_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    _quality_analyses[analysis_id] = result
    
    return json.dumps({
        "status": "success",
        "analysis_id": analysis_id,
        "metrics": result.get("metrics", {})
    })
```

### Example 2: Dependent Agent (Needs Mapping)

```python
def generate_dbt_models(mapping_id: str, workflow_id: str = None) -> str:
    """Generate DBT models from schema mapping."""
    # Check dependency
    if mapping_id not in _schema_mappings:
        return json.dumps({
            "status": "error",
            "message": "Mapping required. Generate one first."
        })
    
    from agents.dbt.model_generator import generate
    
    result = generate(_schema_mappings[mapping_id])
    
    return json.dumps({"status": "success", ...})
```

### Example 3: Chained Agent (Depends on Multiple)

```python
def deploy_to_production(mapping_id: str, validation_id: str, workflow_id: str = None) -> str:
    """Deploy validated data to production."""
    # Check all dependencies
    if mapping_id not in _schema_mappings:
        return json.dumps({"status": "error", "message": "Mapping required"})
    
    if validation_id not in _validation_results:
        return json.dumps({"status": "error", "message": "Validation required"})
    
    # Check validation passed
    validation = _validation_results[validation_id]
    if validation.get("total_errors", 0) > 0:
        return json.dumps({
            "status": "error",
            "message": "Cannot deploy - validation found errors"
        })
    
    from agents.deployment.deployer import deploy
    
    result = deploy(_schema_mappings[mapping_id])
    
    return json.dumps({"status": "success", ...})
```

## Common Patterns

### Pattern 1: Data Flow Agent

Your agent transforms data:
- Input: mapping_id or validation_id
- Processing: Your agent's logic
- Output: Transformed results
- Storage: Store in orchestrator's memory
- Tracking: Update workflow state

### Pattern 2: Analysis Agent

Your agent analyzes data:
- Input: dataset_id or table_id
- Processing: Run analysis
- Output: Metrics and insights
- Storage: Store analysis results
- Tracking: Add to workflow

### Pattern 3: Action Agent

Your agent performs actions:
- Input: Confirmation + parameters
- Processing: Execute action (deploy, load, etc.)
- Output: Action results
- Storage: Store execution logs
- Tracking: Record in workflow

## Need Help?

1. **Look at existing integrations** in `agent.py`
2. **Copy the pattern** for schema_mapping or validation
3. **Test incrementally** - one function at a time
4. **Ask questions** in team chat or documentation

---

**Ready to integrate your agent?**

1. Copy the wrapper function template
2. Modify for your agent
3. Register tools
4. Test locally
5. Submit PR for review

Happy integrating! 🚀

