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
_etl_sql_scripts = {}
_etl_execution_results = {}


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
            is_update = mapping_id in _schema_mappings
            action = "updated" if is_update else "generated"
            
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
                "action": action,
                "is_update": is_update,
                "message": f"Schema mapping {action} successfully" + (" (overwrote existing mapping)" if is_update else ""),
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


# --- ETL Agent Tools (Delegates to ETL Agent) ---

def generate_etl_sql(mapping_id: str, workflow_id: str = None) -> str:
    """
    Generate ETL SQL scripts from a schema mapping.
    
    Takes the JSON mapping from the schema mapping agent and generates
    executable SQL INSERT statements to load data from staging to target tables.

    Args:
        mapping_id: The mapping ID to use for SQL generation
        workflow_id: Optional workflow ID to track this ETL generation

    Returns:
        JSON string with generated SQL scripts
    """
    try:
        # Check if mapping exists
        if mapping_id not in _schema_mappings:
            return json.dumps({
                "status": "error",
                "message": f"Mapping '{mapping_id}' not found",
                "available_mappings": list(_schema_mappings.keys())
            }, indent=2)
        
        # Import the ETL SQL generation function
        from agents.etl_agent.tools.gen_etl_sql import generate_etl_sql_from_json_string
        
        print(f"🔄 Orchestrator: Calling ETL Agent to generate SQL...")
        print(f"   Mapping ID: {mapping_id}")
        
        # Set environment variable for ETL agent to use
        os.environ["GCP_PROJECT_ID"] = project_id
        
        # Get the mapping data
        mapping_data = _schema_mappings[mapping_id]
        
        # Convert mapping to JSON string for ETL agent
        # ETL agent expects the full structure with "mapping" key
        mapping_json = json.dumps(mapping_data)
        print(f"   mapping_json: {mapping_json}")

        # Generate SQL scripts
        sql_scripts = generate_etl_sql_from_json_string(mapping_json)
        
        # Store the generated SQL
        etl_id = f"{mapping_id}_etl"
        _etl_sql_scripts[etl_id] = {
            "mapping_id": mapping_id,
            "sql_scripts": sql_scripts,
            "generated_at": datetime.utcnow().isoformat(),
            "workflow_id": workflow_id
        }
        
        # Update workflow state
        if workflow_id and workflow_id in _workflow_state:
            _workflow_state[workflow_id]["steps"].append({
                "step": "etl_sql_generation",
                "status": "completed",
                "etl_id": etl_id,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        print(f"✅ Orchestrator: ETL SQL generated successfully!")
        print(f"   ETL ID: {etl_id}")
        
        return json.dumps({
            "status": "success",
            "etl_id": etl_id,
            "mapping_id": mapping_id,
            "sql_scripts": sql_scripts,
            "message": "ETL SQL scripts generated successfully. Review the SQL before executing."
        }, indent=2)
            
    except Exception as e:
        error_msg = f"Error generating ETL SQL: {str(e)}"
        print(f"❌ Orchestrator: {error_msg}")
        
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)


def execute_etl_sql(etl_id: str, target_dataset: str, workflow_id: str = None) -> str:
    """
    Execute ETL SQL scripts in BigQuery.
    
    **IMPORTANT**: This will actually load data into your target tables.
    Review the SQL scripts first before executing!

    Args:
        etl_id: The ETL ID (from generate_etl_sql) to execute
        target_dataset: The target BigQuery dataset to load data into
        workflow_id: Optional workflow ID to track this execution

    Returns:
        JSON string with execution results
    """
    try:
        # Check if ETL script exists
        if etl_id not in _etl_sql_scripts:
            return json.dumps({
                "status": "error",
                "message": f"ETL script '{etl_id}' not found",
                "available_etl_scripts": list(_etl_sql_scripts.keys())
            }, indent=2)
        
        # Import the SQL execution function
        from agents.etl_agent.tools.gen_etl_sql import execute_sql
        
        print(f"🔄 Orchestrator: Calling ETL Agent to execute SQL...")
        print(f"   ETL ID: {etl_id}")
        print(f"   Target Dataset: {target_dataset}")
        
        # Set environment variable for ETL agent to use
        os.environ["GCP_PROJECT_ID"] = project_id
        
        # Get the SQL scripts
        etl_data = _etl_sql_scripts[etl_id]
        sql_scripts = etl_data["sql_scripts"]
        
        # Execute the SQL
        result = execute_sql(
            query_sql=sql_scripts,
            dataset_name=target_dataset
        )
        
        # Store execution results
        execution_id = f"{etl_id}_execution"
        _etl_execution_results[execution_id] = {
            "etl_id": etl_id,
            "target_dataset": target_dataset,
            "result": result,
            "executed_at": datetime.utcnow().isoformat(),
            "workflow_id": workflow_id
        }
        
        # Update workflow state
        if workflow_id and workflow_id in _workflow_state:
            _workflow_state[workflow_id]["steps"].append({
                "step": "etl_execution",
                "status": "completed",
                "execution_id": execution_id,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        print(f"✅ Orchestrator: ETL SQL executed successfully!")
        print(f"   Execution ID: {execution_id}")
        
        return json.dumps({
            "status": "success",
            "execution_id": execution_id,
            "etl_id": etl_id,
            "target_dataset": target_dataset,
            "result": result,
            "message": "ETL SQL executed successfully. Data loaded into target tables."
        }, indent=2)
            
    except Exception as e:
        error_msg = f"Error executing ETL SQL: {str(e)}"
        print(f"❌ Orchestrator: {error_msg}")
        
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)


def get_etl_sql(etl_id: str) -> str:
    """
    Retrieve generated ETL SQL scripts by ID.

    Args:
        etl_id: The ETL ID to retrieve

    Returns:
        JSON string with ETL SQL scripts
    """
    if etl_id not in _etl_sql_scripts:
        return json.dumps({
            "status": "error",
            "message": f"ETL script '{etl_id}' not found",
            "available_etl_scripts": list(_etl_sql_scripts.keys())
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "etl_id": etl_id,
        "etl_data": _etl_sql_scripts[etl_id]
    }, indent=2)


def list_etl_scripts() -> str:
    """
    List all ETL SQL scripts generated in this session.

    Returns:
        JSON string with list of ETL scripts
    """
    if not _etl_sql_scripts:
        return json.dumps({
            "status": "success",
            "etl_scripts": [],
            "count": 0,
            "message": "No ETL scripts yet. Use generate_etl_sql() to create one."
        }, indent=2)
    
    scripts_summary = []
    for etl_id, etl_data in _etl_sql_scripts.items():
        scripts_summary.append({
            "etl_id": etl_id,
            "mapping_id": etl_data.get("mapping_id"),
            "generated_at": etl_data.get("generated_at"),
            "workflow_id": etl_data.get("workflow_id")
        })
    
    return json.dumps({
        "status": "success",
        "etl_scripts": scripts_summary,
        "count": len(scripts_summary)
    }, indent=2)


def save_etl_sql_script(sql_script: str, script_id: str, workflow_id: str = None) -> str:
    """
    Save or update a custom ETL SQL script.
    
    Users can save generated SQL or their own modified SQL scripts.
    Same script_id overwrites existing script (for updates).

    Args:
        sql_script: The SQL script to save
        script_id: Unique identifier for this script (e.g., "worldbank_custom_v1")
        workflow_id: Optional workflow ID to track this save

    Returns:
        JSON string with status
    """
    try:
        # Import the save function from ETL agent
        from agents.etl_agent.tools.gen_etl_sql import save_etl_sql
        
        print(f"🔄 Orchestrator: Saving ETL SQL script...")
        print(f"   Script ID: {script_id}")
        
        # Set environment variable for ETL agent to use
        os.environ["GCP_PROJECT_ID"] = project_id
        
        # Call the ETL agent's save function
        result = save_etl_sql(sql_script, script_id)
        
        print(f"✅ Orchestrator: SQL script saved successfully!")
        
        return result
            
    except Exception as e:
        error_msg = f"Error saving ETL SQL script: {str(e)}"
        print(f"❌ Orchestrator: {error_msg}")
        
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)


def load_etl_sql_script(script_id: str) -> str:
    """
    Load a previously saved ETL SQL script.

    Args:
        script_id: The ID of the script to load

    Returns:
        The SQL script or error message
    """
    try:
        # Import the load function from ETL agent
        from agents.etl_agent.tools.gen_etl_sql import load_etl_sql
        
        print(f"🔄 Orchestrator: Loading ETL SQL script...")
        print(f"   Script ID: {script_id}")
        
        # Set environment variable for ETL agent to use
        os.environ["GCP_PROJECT_ID"] = project_id
        
        # Call the ETL agent's load function
        result = load_etl_sql(script_id)
        
        print(f"✅ Orchestrator: SQL script loaded successfully!")
        
        return result
            
    except Exception as e:
        error_msg = f"Error loading ETL SQL script: {str(e)}"
        print(f"❌ Orchestrator: {error_msg}")
        
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)


def list_saved_etl_scripts() -> str:
    """
    List all saved custom ETL SQL scripts.
    
    This shows scripts saved with save_etl_sql_script(), which may include
    user-modified scripts.

    Returns:
        JSON string with list of saved scripts
    """
    try:
        # Import the list function from ETL agent
        from agents.etl_agent.tools.gen_etl_sql import list_etl_sql_scripts
        
        print(f"🔄 Orchestrator: Listing saved ETL SQL scripts...")
        
        # Set environment variable for ETL agent to use
        os.environ["GCP_PROJECT_ID"] = project_id
        
        # Call the ETL agent's list function
        result = list_etl_sql_scripts()
        
        return result
            
    except Exception as e:
        error_msg = f"Error listing saved ETL SQL scripts: {str(e)}"
        print(f"❌ Orchestrator: {error_msg}")
        
        return json.dumps({
            "status": "error",
            "message": error_msg
        }, indent=2)


def execute_saved_etl_script(script_id: str, target_dataset: str, workflow_id: str = None) -> str:
    """
    Execute a saved ETL SQL script by ID.
    
    **IMPORTANT**: This will actually load data into your target tables.
    Review the SQL script first before executing!

    Args:
        script_id: The ID of the saved script to execute
        target_dataset: The target BigQuery dataset to load data into
        workflow_id: Optional workflow ID to track this execution

    Returns:
        JSON string with execution results
    """
    try:
        # Import the execute function from ETL agent
        from agents.etl_agent.tools.gen_etl_sql import execute_sql
        
        print(f"🔄 Orchestrator: Executing saved ETL SQL script...")
        print(f"   Script ID: {script_id}")
        print(f"   Target Dataset: {target_dataset}")
        
        # Set environment variable for ETL agent to use
        os.environ["GCP_PROJECT_ID"] = project_id
        
        # Execute the SQL by script_id
        result = execute_sql(
            script_id=script_id,
            dataset_name=target_dataset
        )
        
        # Store execution results
        execution_id = f"{script_id}_execution"
        _etl_execution_results[execution_id] = {
            "script_id": script_id,
            "target_dataset": target_dataset,
            "result": result,
            "executed_at": datetime.utcnow().isoformat(),
            "workflow_id": workflow_id
        }
        
        # Update workflow state
        if workflow_id and workflow_id in _workflow_state:
            _workflow_state[workflow_id]["steps"].append({
                "step": "saved_etl_execution",
                "status": "completed",
                "execution_id": execution_id,
                "script_id": script_id,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        print(f"✅ Orchestrator: Saved ETL SQL executed successfully!")
        print(f"   Execution ID: {execution_id}")
        
        return json.dumps({
            "status": "success",
            "execution_id": execution_id,
            "script_id": script_id,
            "target_dataset": target_dataset,
            "result": result,
            "message": "Saved ETL SQL executed successfully. Data loaded into target tables."
        }, indent=2)
            
    except Exception as e:
        error_msg = f"Error executing saved ETL SQL: {str(e)}"
        print(f"❌ Orchestrator: {error_msg}")
        
        return json.dumps({
            "status": "error",
            "message": error_msg
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
4. **ETL Agent**: Generates and executes SQL scripts to load data from staging to target tables

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

**ETL Generation & Execution (STAGE 4):**
- `generate_etl_sql(mapping_id, workflow_id)`: Generate SQL scripts from schema mapping
- `execute_etl_sql(etl_id, target_dataset, workflow_id)`: Execute generated ETL SQL (after review!)
- `get_etl_sql(etl_id)`: Retrieve generated SQL scripts
- `list_etl_scripts()`: See all generated ETL scripts
- `save_etl_sql_script(sql_script, script_id, workflow_id)`: Save or update custom SQL scripts
- `load_etl_sql_script(script_id)`: Load a saved SQL script
- `list_saved_etl_scripts()`: See all saved custom SQL scripts
- `execute_saved_etl_script(script_id, target_dataset, workflow_id)`: Execute saved SQL script

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
5. Then `generate_etl_sql()` to create SQL scripts
6. **Important**: Present the SQL to the user for review before executing
7. Only execute with `execute_etl_sql()` after user confirms
8. Track progress with workflow_id
9. Provide detailed results at each step

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

**Workflow 2: Step-by-Step with Review and Custom SQL**
```
User: Map worldbank_staging to worldbank_target
You: [Call generate_schema_mapping]
     Created mapping with X tables. Would you like to:
     1. Review the mapping
     2. Proceed with validation
     
User: Validate it
You: [Call validate_data with the mapping_id]
     Validation complete. Found Y errors in Z tables.
     Would you like to:
     1. Generate ETL SQL scripts
     2. Review validation details
     
User: Generate ETL SQL
You: [Call generate_etl_sql]
     Generated SQL scripts for loading data.
     **IMPORTANT**: Please review the SQL before executing.
     [Show SQL preview]
     Would you like me to:
     1. Execute this SQL
     2. Save it for you to modify
     
User: Save it as worldbank_etl_v1
You: [Call save_etl_sql_script]
     ✓ Saved as 'worldbank_etl_v1'
     
User: [User modifies SQL and provides modified version]
User: Save this modified SQL as worldbank_etl_v1
You: [Call save_etl_sql_script with same ID]
     ✓ Updated 'worldbank_etl_v1' (overwrote existing)
     
User: Execute worldbank_etl_v1 in target dataset
You: [Call execute_saved_etl_script]
     [Shows SQL]
     **IMPORTANT**: Please confirm execution
     
User: Confirm
You: ✓ Data loaded successfully with your custom SQL!
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
- **CRITICAL**: Always show SQL to users before executing (security best practice)
- Never auto-execute SQL without user confirmation
- **ETL Customization**: Always offer to save generated SQL so users can modify it
- Users can save their custom SQL and execute it by script_id
- Same script_id updates/overwrites existing script

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
        # ETL tools (STAGE 4)
        generate_etl_sql,
        execute_etl_sql,
        get_etl_sql,
        list_etl_scripts,
        save_etl_sql_script,
        load_etl_sql_script,
        list_saved_etl_scripts,
        execute_saved_etl_script,
        # Workflow management tools
        run_complete_workflow,
        get_workflow_status,
        list_workflows,
    ],
)

