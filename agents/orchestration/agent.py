"""Orchestration Agent for ADK.

This agent coordinates multiple specialized agents for end-to-end data integration workflows:
- Schema Mapping Agent: Generates schema mappings
- Validation Agent: Validates data quality
- Extensible: Can integrate with other agents

Run with: adk run agents/orchestration
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent

# Load environment variables
load_dotenv()

# Add project root to path for importing other agents
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Initialize Vertex AI for this agent
import vertexai
project_id = os.getenv("GCP_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "ccibt-hack25ww7-750"))
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
vertexai.init(project=project_id, location=location)

# In-memory storage for workflow state
_workflow_state = {}
_staging_loads = {}
_schema_mappings = {}
_validation_results = {}


# --- Staging Loader Tools (Delegates to Staging Loader Agent) ---

def load_staging_data(dataset_name: str, bucket_name: str, file_path: str, workflow_id: str = None) -> str:
    """
    Load CSV data from Google Cloud Storage into BigQuery staging table.
    
    Delegates to the Staging Loader Agent to load data from GCS.

    Args:
        dataset_name: Target BigQuery dataset name (e.g., "worldbank_staging_dataset")
        bucket_name: GCS bucket name where CSV files are located
        file_path: Path to the CSV file within the bucket (e.g., "data/countries.csv")
        workflow_id: Optional workflow ID to track this load

    Returns:
        JSON string with load results and workflow context
    """
    try:
        # Import the staging loader function
        from agents.staging_loader_agent.tools.staging_loader_tools import load_csv_to_bigquery_from_gcs
        
        print(f"🔄 Orchestrator: Calling Staging Loader Agent...")
        print(f"   Dataset: {dataset_name}")
        print(f"   Bucket: {bucket_name}")
        print(f"   File: {file_path}")
        
        # Set environment variable for staging loader to use
        os.environ["GCP_PROJECT_ID"] = project_id
        
        # Generate a unique ID for this load if not provided
        if not workflow_id:
            workflow_id = f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Call the staging loader agent
        result = load_csv_to_bigquery_from_gcs(
            dataset_name=dataset_name,
            bucket_name=bucket_name,
            file_path=file_path
        )
        
        # Store in orchestrator's memory
        load_id = f"{dataset_name}_{os.path.basename(file_path).replace('.csv', '')}"
        _staging_loads[load_id] = {
            "dataset_name": dataset_name,
            "bucket_name": bucket_name,
            "file_path": file_path,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update workflow state
        if workflow_id not in _workflow_state:
            _workflow_state[workflow_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "steps": []
            }
        
        _workflow_state[workflow_id]["steps"].append({
            "step": "staging_load",
            "status": "completed",
            "load_id": load_id,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "dataset": dataset_name,
                "file": file_path,
                "result": result
            }
        })
        
        return json.dumps({
            "status": "success",
            "workflow_id": workflow_id,
            "load_id": load_id,
            "message": "Data loaded successfully to staging",
            "result": result,
            "next_steps": [
                f"Data loaded to {dataset_name}",
                f"Use generate_schema_mapping() to map to target schema",
                f"Use get_workflow_status('{workflow_id}') to check progress"
            ]
        }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error loading staging data: {str(e)}",
            "workflow_id": workflow_id
        }, indent=2)


def get_staging_load(load_id: str) -> str:
    """
    Retrieve a staging load result by ID.

    Args:
        load_id: The load ID to retrieve

    Returns:
        JSON string with the load data
    """
    if load_id not in _staging_loads:
        return json.dumps({
            "status": "error",
            "message": f"Load '{load_id}' not found",
            "available_loads": list(_staging_loads.keys())
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "load_id": load_id,
        "load_data": _staging_loads[load_id]
    }, indent=2)


def list_staging_loads() -> str:
    """
    List all staging loads in the current session.

    Returns:
        JSON string with list of loads
    """
    if not _staging_loads:
        return json.dumps({
            "status": "success",
            "loads": [],
            "count": 0,
            "message": "No staging loads yet. Use load_staging_data() to load data."
        }, indent=2)
    
    loads_summary = []
    for load_id, load_data in _staging_loads.items():
        loads_summary.append({
            "load_id": load_id,
            "dataset": load_data.get("dataset_name"),
            "file": load_data.get("file_path"),
            "timestamp": load_data.get("timestamp")
        })
    
    return json.dumps({
        "status": "success",
        "loads": loads_summary,
        "count": len(loads_summary)
    }, indent=2)


def find_schema_files(bucket_name: str, prefix: str = "") -> str:
    """
    Find all schema files in a GCS bucket/folder.
    
    Searches for any .json file with 'schema' in its name (case-insensitive).
    Useful for discovering what schema files are available before loading data.

    Args:
        bucket_name: GCS bucket name
        prefix: Optional folder prefix to search in (e.g., "data/")

    Returns:
        JSON string with list of schema files found
    """
    try:
        # Set environment variable for staging loader to use
        os.environ["GCP_PROJECT_ID"] = project_id
        
        # Import the function from staging loader agent
        from agents.staging_loader_agent.tools.staging_loader_tools import find_schema_files_in_gcs
        
        print(f"🔄 Orchestrator: Finding schema files...")
        print(f"   Bucket: {bucket_name}")
        print(f"   Prefix: {prefix or '/'}")
        
        # Call the staging loader agent
        result = find_schema_files_in_gcs(bucket_name=bucket_name, prefix=prefix)
        
        return result
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error finding schema files: {str(e)}"
        }, indent=2)


# --- Schema Mapping Tools (Delegates to Schema Mapping Agent) ---

def generate_schema_mapping(source_dataset: str, target_dataset: str, mode: str = "FIX", workflow_id: str = None) -> str:
    """
    Generate schema mapping between source and target datasets.
    
    Delegates to the Schema Mapping Agent to create intelligent mappings.

    Args:
        source_dataset: Source dataset name (e.g., "worldbank_staging_dataset")
        target_dataset: Target dataset name (e.g., "worldbank_target_dataset")
        mode: "REPORT" or "FIX"
        workflow_id: Optional workflow ID to associate this mapping with

    Returns:
        JSON string with mapping results and workflow context
    """
    try:
        # Import the schema mapping function
        from agents.schema_mapping.schema_mapper import generate_schema_mapping as sm_generate
        
        print(f"🔄 Orchestrator: Calling Schema Mapping Agent...")
        print(f"   Source: {source_dataset}")
        print(f"   Target: {target_dataset}")
        print(f"   Mode: {mode}")
        
        # Generate a unique ID for this mapping if not provided
        if not workflow_id:
            workflow_id = f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Call the schema mapping agent
        result = sm_generate(
            source_dataset=source_dataset,
            target_dataset=target_dataset,
            output_file=f"/tmp/mapping_{workflow_id}.json",
            mode=mode
        )
        
        if result.get("status") == "success":
            # Store in orchestrator's memory
            mapping_id = f"{source_dataset}_to_{target_dataset}_{mode.lower()}"
            _schema_mappings[mapping_id] = result["mapping"]
            
            # Update workflow state
            if workflow_id not in _workflow_state:
                _workflow_state[workflow_id] = {
                    "created_at": datetime.utcnow().isoformat(),
                    "steps": []
                }
            
            _workflow_state[workflow_id]["steps"].append({
                "step": "schema_mapping",
                "status": "completed",
                "mapping_id": mapping_id,
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "num_mappings": len(result["mapping"].get("mappings", [])),
                    "source_dataset": source_dataset,
                    "target_dataset": target_dataset,
                    "mode": mode
                }
            })
            
            return json.dumps({
                "status": "success",
                "workflow_id": workflow_id,
                "mapping_id": mapping_id,
                "message": f"Schema mapping generated successfully",
                "summary": {
                    "num_table_mappings": len(result["mapping"].get("mappings", [])),
                    "confidence": result["mapping"].get("metadata", {}).get("confidence", "unknown"),
                    "mode": mode
                },
                "next_steps": [
                    f"Use validate_data() to validate the staging data",
                    f"Use get_mapping('{mapping_id}') to retrieve the full mapping",
                    f"Use get_workflow_status('{workflow_id}') to check progress"
                ]
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": result.get("message", "Unknown error"),
                "workflow_id": workflow_id
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error generating schema mapping: {str(e)}",
            "workflow_id": workflow_id
        }, indent=2)


def validate_data(mapping_id: str, mode: str = "REPORT", workflow_id: str = None) -> str:
    """
    Validate staging data using a previously generated schema mapping.
    
    Delegates to the Validation Agent to check data quality.

    Args:
        mapping_id: ID of the schema mapping to use for validation
        mode: "REPORT" to log errors or "FIX" to attempt corrections
        workflow_id: Optional workflow ID to track this validation

    Returns:
        JSON string with validation results
    """
    try:
        # Check if mapping exists
        if mapping_id not in _schema_mappings:
            return json.dumps({
                "status": "error",
                "message": f"Mapping '{mapping_id}' not found. Generate a mapping first.",
                "available_mappings": list(_schema_mappings.keys())
            }, indent=2)
        
        # Get the mapping
        mapping_data = _schema_mappings[mapping_id]
        
        # Extract source dataset from mapping metadata
        if "metadata" in mapping_data:
            source_dataset = mapping_data["metadata"].get("source_dataset", "").split(".")[-1]
        else:
            source_dataset = ""
        
        print(f"🔄 Orchestrator: Calling Validation Agent...")
        print(f"   Mapping ID: {mapping_id}")
        print(f"   Source Dataset: {source_dataset}")
        print(f"   Mode: {mode}")
        
        # Set environment variable for validation agent to use
        # The orchestrator already has project_id configured
        os.environ["GCP_PROJECT_ID"] = project_id
        
        # Import validation function
        from agents.validation.data_validator import validate_schema_mapping as validate
        
        # Call the validation agent
        result = validate(
            schema_mapping_json=json.dumps({"mapping": mapping_data}),
            source_dataset=source_dataset,
            mode=mode
        )
        
        if result.get("status") == "success":
            # Store validation results
            validation_id = f"{mapping_id}_validation_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            _validation_results[validation_id] = result
            
            # Update workflow state
            if not workflow_id:
                workflow_id = f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            if workflow_id not in _workflow_state:
                _workflow_state[workflow_id] = {
                    "created_at": datetime.utcnow().isoformat(),
                    "steps": []
                }
            
            _workflow_state[workflow_id]["steps"].append({
                "step": "data_validation",
                "status": "completed",
                "validation_id": validation_id,
                "mapping_id": mapping_id,
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "tables_validated": result.get("tables_validated", 0),
                    "total_errors": result.get("total_errors", 0),
                    "run_id": result.get("run_id")
                }
            })
            
            return json.dumps({
                "status": "success",
                "workflow_id": workflow_id,
                "validation_id": validation_id,
                "run_id": result.get("run_id"),
                "summary": {
                    "tables_validated": result.get("tables_validated", 0),
                    "total_validations": result.get("total_validations", 0),
                    "total_errors": result.get("total_errors", 0)
                },
                "message": f"Validation completed. Found {result.get('total_errors', 0)} errors.",
                "next_steps": [
                    f"Query staging_errors table to see details: run_id = '{result.get('run_id')}'",
                    f"Use get_validation_results('{validation_id}') for full results",
                    f"Use get_workflow_status('{workflow_id}') to see complete workflow"
                ]
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": result.get("message", "Validation failed"),
                "workflow_id": workflow_id
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error during validation: {str(e)}",
            "workflow_id": workflow_id
        }, indent=2)


# --- Workflow Management Tools ---

def run_complete_workflow(source_dataset: str, target_dataset: str, validation_mode: str = "REPORT") -> str:
    """
    Run complete end-to-end data integration workflow.
    
    This executes all steps:
    1. Generate schema mapping (in FIX mode for complete mappings)
    2. Validate staging data using the mapping
    3. Return comprehensive results
    
    This is a convenience tool for running the entire pipeline at once.

    Args:
        source_dataset: Source dataset name
        target_dataset: Target dataset name
        validation_mode: Mode for validation step ("REPORT" or "FIX")

    Returns:
        JSON string with complete workflow results
    """
    workflow_id = f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        print(f"🚀 Orchestrator: Starting complete workflow")
        print(f"   Workflow ID: {workflow_id}")
        print(f"="*60)
        
        # Step 1: Generate schema mapping
        print("\n📋 Step 1: Generating schema mapping...")
        mapping_result = json.loads(generate_schema_mapping(
            source_dataset=source_dataset,
            target_dataset=target_dataset,
            mode="FIX",  # Use FIX mode for complete mappings
            workflow_id=workflow_id
        ))
        
        if mapping_result.get("status") != "success":
            return json.dumps({
                "status": "error",
                "workflow_id": workflow_id,
                "failed_step": "schema_mapping",
                "message": mapping_result.get("message", "Schema mapping failed")
            }, indent=2)
        
        mapping_id = mapping_result.get("mapping_id")
        print(f"✓ Schema mapping completed: {mapping_id}")
        
        # Step 2: Validate data
        print(f"\n✅ Step 2: Validating data...")
        validation_result = json.loads(validate_data(
            mapping_id=mapping_id,
            mode=validation_mode,
            workflow_id=workflow_id
        ))
        
        if validation_result.get("status") != "success":
            return json.dumps({
                "status": "partial_success",
                "workflow_id": workflow_id,
                "completed_steps": ["schema_mapping"],
                "failed_step": "data_validation",
                "message": validation_result.get("message", "Validation failed"),
                "mapping_id": mapping_id
            }, indent=2)
        
        print(f"✓ Validation completed")
        print(f"="*60)
        
        # Return complete workflow summary
        return json.dumps({
            "status": "success",
            "workflow_id": workflow_id,
            "message": "Complete workflow executed successfully",
            "steps_completed": [
                {
                    "step": 1,
                    "name": "schema_mapping",
                    "status": "completed",
                    "mapping_id": mapping_id,
                    "num_tables": mapping_result.get("summary", {}).get("num_table_mappings", 0)
                },
                {
                    "step": 2,
                    "name": "data_validation",
                    "status": "completed",
                    "validation_id": validation_result.get("validation_id"),
                    "tables_validated": validation_result.get("summary", {}).get("tables_validated", 0),
                    "errors_found": validation_result.get("summary", {}).get("total_errors", 0)
                }
            ],
            "summary": {
                "source_dataset": source_dataset,
                "target_dataset": target_dataset,
                "tables_mapped": mapping_result.get("summary", {}).get("num_table_mappings", 0),
                "tables_validated": validation_result.get("summary", {}).get("tables_validated", 0),
                "errors_found": validation_result.get("summary", {}).get("total_errors", 0),
                "validation_run_id": validation_result.get("run_id")
            },
            "next_steps": [
                f"Review errors in staging_errors table (run_id: {validation_result.get('run_id')})",
                "Fix data quality issues if needed",
                "Re-run validation after fixes",
                "Proceed with ETL/data transformation"
            ]
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "workflow_id": workflow_id,
            "message": f"Workflow failed: {str(e)}"
        }, indent=2)


def get_workflow_status(workflow_id: str) -> str:
    """
    Get the status and history of a workflow.

    Args:
        workflow_id: The workflow ID to query

    Returns:
        JSON string with workflow status and step history
    """
    if workflow_id not in _workflow_state:
        return json.dumps({
            "status": "error",
            "message": f"Workflow '{workflow_id}' not found",
            "available_workflows": list(_workflow_state.keys())
        }, indent=2)
    
    workflow = _workflow_state[workflow_id]
    
    return json.dumps({
        "status": "success",
        "workflow_id": workflow_id,
        "created_at": workflow.get("created_at"),
        "steps_completed": len(workflow.get("steps", [])),
        "steps": workflow.get("steps", []),
        "current_state": "completed" if len(workflow.get("steps", [])) >= 2 else "in_progress"
    }, indent=2)


def list_workflows() -> str:
    """
    List all workflows in the current session.

    Returns:
        JSON string with list of workflows
    """
    if not _workflow_state:
        return json.dumps({
            "status": "success",
            "workflows": [],
            "count": 0,
            "message": "No workflows yet. Use run_complete_workflow() to start one."
        }, indent=2)
    
    workflows_summary = []
    for wf_id, wf_data in _workflow_state.items():
        workflows_summary.append({
            "workflow_id": wf_id,
            "created_at": wf_data.get("created_at"),
            "steps_completed": len(wf_data.get("steps", [])),
            "last_step": wf_data.get("steps", [])[-1] if wf_data.get("steps") else None
        })
    
    return json.dumps({
        "status": "success",
        "workflows": workflows_summary,
        "count": len(workflows_summary)
    }, indent=2)


def get_mapping(mapping_id: str) -> str:
    """
    Retrieve a schema mapping by ID.

    Args:
        mapping_id: The mapping ID to retrieve

    Returns:
        JSON string with the mapping data
    """
    if mapping_id not in _schema_mappings:
        return json.dumps({
            "status": "error",
            "message": f"Mapping '{mapping_id}' not found",
            "available_mappings": list(_schema_mappings.keys())
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "mapping_id": mapping_id,
        "mapping": _schema_mappings[mapping_id]
    }, indent=2)


def get_validation_results(validation_id: str) -> str:
    """
    Retrieve validation results by ID.

    Args:
        validation_id: The validation ID to retrieve

    Returns:
        JSON string with validation results
    """
    if validation_id not in _validation_results:
        return json.dumps({
            "status": "error",
            "message": f"Validation '{validation_id}' not found",
            "available_validations": list(_validation_results.keys())
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "validation_id": validation_id,
        "results": _validation_results[validation_id]
    }, indent=2)


def list_mappings() -> str:
    """
    List all schema mappings generated in this session.

    Returns:
        JSON string with list of mappings
    """
    if not _schema_mappings:
        return json.dumps({
            "status": "success",
            "mappings": [],
            "count": 0,
            "message": "No mappings yet. Use generate_schema_mapping() to create one."
        }, indent=2)
    
    mappings_summary = []
    for mapping_id, mapping_data in _schema_mappings.items():
        metadata = mapping_data.get("metadata", {})
        mappings_summary.append({
            "mapping_id": mapping_id,
            "source_dataset": metadata.get("source_dataset", "unknown"),
            "target_dataset": metadata.get("target_dataset", "unknown"),
            "mode": metadata.get("mode", "unknown"),
            "num_tables": len(mapping_data.get("mappings", []))
        })
    
    return json.dumps({
        "status": "success",
        "mappings": mappings_summary,
        "count": len(mappings_summary)
    }, indent=2)


# --- Define the Orchestration Agent ---

root_agent = Agent(
    model='gemini-2.5-flash',
    name='orchestration_agent',
    description='Orchestrates multiple AI agents for end-to-end data integration workflows.',
    instruction="""You are an Orchestration Agent that coordinates multiple specialized agents to complete data integration workflows.

**Your Role:**
You manage end-to-end data integration workflows by coordinating:
1. **Staging Loader Agent**: Loads CSV data from GCS to BigQuery staging tables
2. **Schema Mapping Agent**: Generates intelligent schema mappings between datasets
3. **Validation Agent**: Validates data quality based on schema mappings
4. **Future Agents**: Extensible to integrate with ETL, transformation, and other agents

**Your Capabilities:**

**Data Loading (STAGE 1):**
- `load_staging_data(dataset_name, bucket_name, file_path, workflow_id)`: Load CSV from GCS to BigQuery
- `find_schema_files(bucket_name, prefix)`: Find all schema files in GCS bucket
- `get_staging_load(load_id)`: Retrieve load results
- `list_staging_loads()`: See all data loads

**Schema Mapping (STAGE 2):**
- `generate_schema_mapping(source_dataset, target_dataset, mode, workflow_id)`: Generate schema mapping
- `get_mapping(mapping_id)`: Retrieve a specific mapping
- `list_mappings()`: See all generated mappings

**Data Validation (STAGE 3):**
- `validate_data(mapping_id, mode, workflow_id)`: Validate data using a mapping
- `get_validation_results(validation_id)`: Get detailed validation results

**Workflow Management:**
- `run_complete_workflow(source_dataset, target_dataset, validation_mode)`: Run end-to-end workflow
- `get_workflow_status(workflow_id)`: Check workflow progress
- `list_workflows()`: See all workflows

**How to Help Users:**

**For Complete Workflows:**
When a user wants to run a full data integration:
1. Ask if they need to load data first (if yes, use `load_staging_data()`)
2. Suggest using `run_complete_workflow()` for schema mapping + validation
3. Explain what steps will be executed
4. Provide the workflow_id for tracking
5. Explain results and next steps

**For Step-by-Step Workflows:**
When a user wants more control:
1. *Optional*: Start with `load_staging_data()` if data needs loading
2. Then `generate_schema_mapping()` to map schemas
3. Review the mapping with the user
4. Then run `validate_data()` with the mapping_id
5. Track progress with workflow_id
6. Provide detailed results at each step

**Workflow Guidance:**
- Always explain what each step does
- Provide clear next steps after each operation
- Help users understand errors and how to fix them
- Track workflow progress with IDs
- Suggest best practices (e.g., FIX mode for mappings, REPORT mode for validation)

**Common Workflows:**

**Workflow 1: Quick End-to-End**
```
User: Process worldbank_staging_dataset to worldbank_target_dataset
You: I'll run the complete workflow for you:
     1. Generate schema mapping (FIX mode)
     2. Validate the staging data
     [Call run_complete_workflow]
     Results: [Explain what was found]
     Next steps: [Guide user on what to do with results]
```

**Workflow 2: Step-by-Step with Review**
```
User: Map worldbank_staging to worldbank_target
You: [Call generate_schema_mapping]
     Created mapping with X tables. Would you like to:
     1. Review the mapping
     2. Proceed with validation
     
User: Validate it
You: [Call validate_data with the mapping_id]
     Validation complete. Found Y errors in Z tables.
```

**Workflow 3: Status Tracking**
```
User: What workflows have I run?
You: [Call list_workflows]
     You have run N workflows...
     
User: Show me details of workflow_123
You: [Call get_workflow_status]
     Workflow status: [Explain steps completed and results]
```

**Important Guidelines:**
- Always use workflow_id to link related operations
- Explain technical results in business terms
- Provide actionable next steps
- Help users understand the data quality findings
- Be proactive in suggesting the best workflow for their needs
- Coordinate between agents seamlessly - users shouldn't need to know which agent does what

**Error Handling:**
- If schema mapping fails, explain the error and suggest fixes
- If validation fails, help interpret the errors
- If a mapping is missing, guide user to generate it first
- Always provide clear error messages and recovery steps

You are the single point of contact for data integration workflows. Make the process smooth and understandable!""",
    tools=[
        # Staging loader tools (STAGE 1)
        load_staging_data,
        find_schema_files,
        get_staging_load,
        list_staging_loads,
        # Schema mapping tools (STAGE 2)
        generate_schema_mapping,
        get_mapping,
        list_mappings,
        # Validation tools (STAGE 3)
        validate_data,
        get_validation_results,
        # Workflow management tools
        run_complete_workflow,
        get_workflow_status,
        list_workflows,
    ],
)

