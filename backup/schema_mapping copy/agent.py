"""Schema Mapping Agent for ADK.

This agent generates intelligent schema mappings between BigQuery datasets using Gemini.
Run with: adk run agents/schema_mapping
"""

import os
import json
from datetime import datetime
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent

# Load environment variables
load_dotenv()

# Configuration
project_id = os.getenv("GCP_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "ccibt-hack25ww7-750"))
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Initialize Vertex AI
vertexai.init(project=project_id, location=location)

# BigQuery client (initialized once)
bq_client = bigquery.Client(project=project_id)

# In-memory storage for mappings (per session)
_mapping_store = {}


# --- State Management Tools ---

def save_mapping(mapping_json: str, mapping_id: str) -> str:
    """
    Save a mapping to memory with an ID for later retrieval.
    
    Use this to store generated mappings so you can reference them later,
    extract parts, modify them, or use them with other operations.

    Args:
        mapping_json: The JSON string of the mapping to save
        mapping_id: A unique identifier for this mapping (e.g., "prod_v1", "test_mapping")

    Returns:
        JSON string with status and list of available mappings
    """
    try:
        # Validate it's valid JSON
        json.loads(mapping_json)
        
        _mapping_store[mapping_id] = mapping_json
        
        return json.dumps({
            "status": "success",
            "message": f"Mapping saved as '{mapping_id}'",
            "mapping_id": mapping_id,
            "available_mappings": list(_mapping_store.keys()),
            "total_saved": len(_mapping_store)
        }, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "message": f"Invalid JSON: {str(e)}"
        })


def load_mapping(mapping_id: str) -> str:
    """
    Load a previously saved mapping by its ID.
    
    Retrieves a mapping that was saved earlier in this session.
    Use this to access mappings for review, modification, or extraction.

    Args:
        mapping_id: The identifier of the mapping to load

    Returns:
        The mapping JSON string if found, or error message
    """
    if mapping_id not in _mapping_store:
        return json.dumps({
            "status": "error",
            "message": f"Mapping '{mapping_id}' not found",
            "available_mappings": list(_mapping_store.keys()),
            "hint": "Use list_mappings to see all saved mappings"
        }, indent=2)
    
    return _mapping_store[mapping_id]


def list_mappings() -> str:
    """
    List all saved mappings in the current session.
    
    Shows all mappings that have been saved with save_mapping.
    Useful to see what's available before loading.

    Returns:
        JSON string with list of saved mapping IDs
    """
    if not _mapping_store:
        return json.dumps({
            "status": "success",
            "saved_mappings": [],
            "count": 0,
            "message": "No mappings saved yet. Generate a mapping and save it to get started."
        }, indent=2)
    
    # Get basic info about each mapping
    mapping_info = []
    for mapping_id, mapping_json in _mapping_store.items():
        try:
            mapping_data = json.loads(mapping_json)
            # Extract metadata if it's a schema mapping
            if isinstance(mapping_data, dict) and "mapping" in mapping_data:
                metadata = mapping_data.get("mapping", {}).get("metadata", {})
                num_mappings = len(mapping_data.get("mapping", {}).get("mappings", []))
                mapping_info.append({
                    "id": mapping_id,
                    "source_dataset": metadata.get("source_dataset", "unknown"),
                    "target_dataset": metadata.get("target_dataset", "unknown"),
                    "mode": metadata.get("mode", "unknown"),
                    "num_table_mappings": num_mappings
                })
            else:
                mapping_info.append({
                    "id": mapping_id,
                    "type": "unknown",
                    "size_bytes": len(mapping_json)
                })
        except:
            mapping_info.append({
                "id": mapping_id,
                "type": "invalid",
                "size_bytes": len(mapping_json)
            })
    
    return json.dumps({
        "status": "success",
        "saved_mappings": mapping_info,
        "count": len(_mapping_store),
        "mapping_ids": list(_mapping_store.keys())
    }, indent=2)


def extract_validation_rules(mapping_id: str, table_name: str = None) -> str:
    """
    Extract validation rules from a saved mapping.
    
    Gets validation rules for all tables or a specific table.
    Useful for passing validation rules to validation agents.

    Args:
        mapping_id: The ID of the saved mapping
        table_name: Optional - specific table name to extract rules for

    Returns:
        JSON string with validation rules
    """
    if mapping_id not in _mapping_store:
        return json.dumps({
            "status": "error",
            "message": f"Mapping '{mapping_id}' not found",
            "available_mappings": list(_mapping_store.keys())
        }, indent=2)
    
    try:
        mapping_json = _mapping_store[mapping_id]
        mapping_data = json.loads(mapping_json)
        
        # Handle both direct mapping format and wrapped format
        if "mapping" in mapping_data:
            mappings = mapping_data["mapping"].get("mappings", [])
        else:
            mappings = mapping_data.get("mappings", [])
        
        if table_name:
            # Extract for specific table
            for table_mapping in mappings:
                target_table = table_mapping.get("target_table", "")
                if table_name in target_table:
                    return json.dumps({
                        "status": "success",
                        "table": target_table,
                        "validation_rules": table_mapping.get("validation_rules", []),
                        "count": len(table_mapping.get("validation_rules", []))
                    }, indent=2)
            
            return json.dumps({
                "status": "error",
                "message": f"Table '{table_name}' not found in mapping",
                "available_tables": [m.get("target_table") for m in mappings]
            }, indent=2)
        else:
            # Extract all validation rules
            all_rules = {}
            for table_mapping in mappings:
                target_table = table_mapping.get("target_table", "unknown")
                all_rules[target_table] = table_mapping.get("validation_rules", [])
            
            return json.dumps({
                "status": "success",
                "validation_rules_by_table": all_rules,
                "total_tables": len(all_rules),
                "total_rules": sum(len(rules) for rules in all_rules.values())
            }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error extracting validation rules: {str(e)}"
        })


def delete_mapping(mapping_id: str) -> str:
    """
    Delete a saved mapping from memory.
    
    Removes a mapping that's no longer needed.

    Args:
        mapping_id: The ID of the mapping to delete

    Returns:
        JSON string with status
    """
    if mapping_id not in _mapping_store:
        return json.dumps({
            "status": "error",
            "message": f"Mapping '{mapping_id}' not found",
            "available_mappings": list(_mapping_store.keys())
        }, indent=2)
    
    del _mapping_store[mapping_id]
    
    return json.dumps({
        "status": "success",
        "message": f"Mapping '{mapping_id}' deleted",
        "remaining_mappings": list(_mapping_store.keys()),
        "count": len(_mapping_store)
    }, indent=2)


# --- Tool Functions ---

def fetch_table_schema(full_table_id: str) -> str:
    """
    Fetch schema information from a BigQuery table.

    Args:
        full_table_id: Format: "project.dataset.table"

    Returns:
        JSON string with table metadata and column info
    """
    try:
        table = bq_client.get_table(full_table_id)

        columns = []
        for field in table.schema:
            columns.append({
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,  # REQUIRED, NULLABLE, REPEATED
                "description": field.description or ""
            })

        result = {
            "table_id": full_table_id,
            "num_rows": table.num_rows,
            "columns": columns
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def fetch_dataset_schemas(dataset_id: str) -> str:
    """
    Fetch all table schemas from a BigQuery dataset.

    Args:
        dataset_id: Format: "project.dataset" or just "dataset"

    Returns:
        JSON string mapping table names to their schemas
    """
    if '.' not in dataset_id:
        dataset_id = f"{project_id}.{dataset_id}"

    try:
        tables = bq_client.list_tables(dataset_id)
        schemas = {}

        for table in tables:
            full_table_id = f"{dataset_id}.{table.table_id}"
            table_obj = bq_client.get_table(full_table_id)
            
            columns = []
            for field in table_obj.schema:
                columns.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description or ""
                })
            
            schemas[table.table_id] = {
                "table_id": full_table_id,
                "num_rows": table_obj.num_rows,
                "columns": columns
            }

        return json.dumps(schemas, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def generate_schema_mapping(source_dataset: str, target_dataset: str, mode: str = "REPORT") -> str:
    """
    Generate intelligent schema mapping between source and target BigQuery datasets.
    
    This function uses LLM to analyze schemas and create mappings including:
    - Table matching (source → target)
    - Column mappings with type conversions
    - Validation rules (NOT_NULL, NUMERIC, RANGE)
    - Primary keys and uniqueness constraints
    - Handling of unmapped columns

    Args:
        source_dataset: Source BigQuery dataset name (e.g., "worldbank_staging_dataset")
        target_dataset: Target BigQuery dataset name (e.g., "worldbank_target_dataset")
        mode: "REPORT" (flag unmapped columns) or "FIX" (suggest defaults)

    Returns:
        JSON string with complete schema mapping or error message
    """
    try:
        # Fetch schemas from BigQuery
        print(f"Fetching schemas from {source_dataset}...")
        source_schemas_str = fetch_dataset_schemas(source_dataset)
        source_schemas = json.loads(source_schemas_str)
        
        if "error" in source_schemas:
            return json.dumps({
                "status": "error",
                "message": f"Error fetching source schemas: {source_schemas['error']}"
            })

        print(f"Fetching schemas from {target_dataset}...")
        target_schemas_str = fetch_dataset_schemas(target_dataset)
        target_schemas = json.loads(target_schemas_str)
        
        if "error" in target_schemas:
            return json.dumps({
                "status": "error",
                "message": f"Error fetching target schemas: {target_schemas['error']}"
            })

        # Generate mapping with LLM
        print("Generating schema mapping with Gemini...")
        mapping_data = _generate_mapping_with_llm(
            source_schemas,
            target_schemas,
            source_dataset,
            target_dataset,
            mode
        )

        if "error" in mapping_data:
            return json.dumps({
                "status": "error",
                "message": mapping_data["error"]
            })

        # Add success status
        result = {
            "status": "success",
            "mapping": mapping_data,
            "summary": {
                "source_dataset": source_dataset,
                "target_dataset": target_dataset,
                "mode": mode,
                "num_mappings": len(mapping_data.get("mappings", [])),
                "confidence": mapping_data.get("metadata", {}).get("confidence", "unknown")
            }
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        })


def _generate_mapping_with_llm(source_schemas: dict, target_schemas: dict,
                                source_dataset: str, target_dataset: str, mode: str) -> dict:
    """
    Internal function: Use Gemini to analyze schemas and generate mapping JSON.
    """
    # Define the tool/function declaration for structured output
    submit_mapping_func = FunctionDeclaration(
        name="submit_schema_mapping",
        description="Submit the final schema mapping JSON with all table and column mappings",
        parameters={
            "type": "object",
            "properties": {
                "mapping_json": {
                    "type": "string",
                    "description": "Complete JSON string containing schema mappings"
                }
            },
            "required": ["mapping_json"]
        }
    )

    mapping_tool = Tool(function_declarations=[submit_mapping_func])

    # Create model with function calling
    model = GenerativeModel(
        "gemini-2.5-flash",
        tools=[mapping_tool]
    )

    # Prepare the prompt
    prompt = f"""
You are a Senior Data Engineer specializing in schema mapping and data migration.

TASK: Generate a comprehensive schema mapping between source and target BigQuery datasets.

SOURCE DATASET: {project_id}.{source_dataset}
SOURCE TABLES & SCHEMAS:
{json.dumps(source_schemas, indent=2)}

TARGET DATASET: {project_id}.{target_dataset}
TARGET TABLES & SCHEMAS:
{json.dumps(target_schemas, indent=2)}

REQUIREMENTS:

1. TABLE MATCHING:
   - Match source tables to target tables (consider name similarity and purpose)
   - Note: Target may have dimensional model (fact/dim tables) while source has flat tables
   - Consider how multiple source tables might map to single target tables

2. COLUMN MAPPING MODE: {mode}

   **REPORT MODE**:
   - For target columns with NO matching source column, set:
     * source_column: "UNMAPPED"
     * source_type: "MISSING"
     * transformation: null
     * notes: "No source column found - requires manual mapping or default value"
   - Add these unmapped columns to "unmapped_target_columns" list
   - Add to "mapping_errors" array for reporting

   **FIX MODE**:
   - For target columns with NO matching source column, suggest best defaults:
     * source_column: "GENERATED"
     * source_type: "EXPRESSION"
     * transformation: Provide DEFAULT value expression with clear prefix
       - Format: "DEFAULT: <expression>"
       - Examples:
         * "DEFAULT: CURRENT_TIMESTAMP()" (not just "CURRENT_TIMESTAMP()")
         * "DEFAULT: 'staging_gdp'" (not just "'staging_gdp'")
         * "DEFAULT: UUID()" (not just "UUID()")
         * "DEFAULT: 0" (not just "0")
     * notes: Explain why this default is appropriate
   - Use intelligent defaults based on column type and name:
     * timestamp/loaded_at columns → "DEFAULT: CURRENT_TIMESTAMP()"
     * data_source/source columns → "DEFAULT: 'source_table_name'"
     * id columns → "DEFAULT: UUID()" or "DEFAULT: ROW_NUMBER() OVER (ORDER BY ...)"
     * audit columns (created_by, etc.) → "DEFAULT: 'SYSTEM'"
     * numeric columns → "DEFAULT: 0"
     * string columns → "DEFAULT: 'UNKNOWN'"

   For all modes:
   - Map each source column to appropriate target column(s)
   - Consider: exact name match, similar names, data types, business meaning
   - NEVER use null for source_column or source_type

3. TYPE CONVERSION:
   - Identify where source and target types differ
   - Note if safe (STRING→STRING) or needs casting (STRING→INT64)

4. VALIDATION RULES:
   Generate rules based on:
   - Target column mode (REQUIRED → NOT_NULL rule)
   - Data type constraints (INTEGER/FLOAT → NUMERIC rule)
   - Reasonable ranges (year: 1900-2100, percentage: 0-100)
   - ID fields should have uniqueness

5. PRIMARY KEYS:
   - Identify likely primary keys (columns with "id", "code", "key")
   - Note composite keys if needed

OUTPUT: Call submit_schema_mapping with a VALID JSON STRING (not Python dict syntax).

CRITICAL JSON FORMATTING RULES:
- Use "true"/"false" NOT "True"/"False"
- Use "null" NOT "None"
- Use double quotes for all strings
- NEVER wrap JSON in Python variables (NO `mapping_json = ...`)
- NEVER use Python functions (NO `print()`, `json.dumps()`, etc.)
- NO Python code whatsoever - provide pure JSON string only
- NO comments in JSON (no # or //)
- Call submit_schema_mapping with ONLY the JSON string, nothing else

JSON structure:

{{
  "metadata": {{
    "source_dataset": "{project_id}.{source_dataset}",
    "target_dataset": "{project_id}.{target_dataset}",
    "generated_at": "{datetime.utcnow().isoformat()}Z",
    "confidence": "high",
    "mode": "{mode}"
  }},
  "mappings": [
    {{
      "source_table": "{source_dataset}.table_name",
      "target_table": "{target_dataset}.table_name",
      "match_confidence": 0.95,
      "column_mappings": [
        {{
          "source_column": "col1",
          "target_column": "col1",
          "source_type": "STRING",
          "target_type": "STRING",
          "type_conversion_needed": false,
          "transformation": null,
          "notes": "Direct mapping"
        }},
        {{
          "source_column": "GENERATED",
          "target_column": "loaded_at",
          "source_type": "EXPRESSION",
          "target_type": "TIMESTAMP",
          "type_conversion_needed": false,
          "transformation": "DEFAULT: CURRENT_TIMESTAMP()",
          "notes": "Auto-generated timestamp for audit purposes"
        }}
      ],
      "unmapped_source_columns": [],
      "unmapped_target_columns": [],
      "mapping_errors": [
        {{
          "error_type": "UNMAPPED_TARGET_COLUMN",
          "target_column": "column_name",
          "severity": "WARNING",
          "message": "Description of issue"
        }}
      ],
      "validation_rules": [
        {{
          "column": "col1",
          "type": "NOT_NULL",
          "reason": "Target column is REQUIRED"
        }}
      ],
      "primary_key": ["col1"],
      "uniqueness_constraints": ["col1"]
    }}
  ]
}}

Call the submit_schema_mapping function with the complete mapping JSON now.
"""

    # Generate content with function calling
    chat = model.start_chat()
    response = chat.send_message(prompt)

    # Extract function call
    if response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.function_call:
                func_call = part.function_call
                if func_call.name == "submit_schema_mapping":
                    mapping_json_str = func_call.args["mapping_json"]

                    # Parse and validate JSON
                    try:
                        mapping_data = json.loads(mapping_json_str)
                        print("✓ LLM generated valid mapping JSON")
                        return mapping_data
                    except json.JSONDecodeError as e:
                        print(f"✗ LLM generated invalid JSON: {e}")
                        return {"error": f"Invalid JSON: {e}"}

    # If no function call, try to extract JSON from text
    print("⚠ No function call found, trying to extract JSON from response text...")
    response_text = response.text

    # Try to find JSON in response
    if "{" in response_text and "}" in response_text:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        json_str = response_text[start:end]
        try:
            mapping_data = json.loads(json_str)
            return mapping_data
        except:
            pass

    return {"error": "Failed to extract mapping from LLM response", "response": response_text}


# --- Define the ADK Agent ---

root_agent = Agent(
    model='gemini-2.5-flash',
    name='schema_mapping_agent',
    description='Generates intelligent schema mappings between BigQuery datasets using LLM analysis with session memory.',
    instruction="""You are a Schema Mapping Agent that helps users generate intelligent mappings between BigQuery datasets.

Your capabilities:

**Schema Analysis:**
1. **fetch_table_schema**: Get detailed schema for a specific BigQuery table
2. **fetch_dataset_schemas**: Get all table schemas from a BigQuery dataset
3. **generate_schema_mapping**: Generate comprehensive schema mappings between source and target datasets

**State Management:**
4. **save_mapping**: Save a generated mapping with an ID for later use
5. **load_mapping**: Load a previously saved mapping by ID
6. **list_mappings**: List all saved mappings in this session
7. **extract_validation_rules**: Extract validation rules from a saved mapping
8. **delete_mapping**: Delete a saved mapping

**Workflow:**

When a user asks to create a schema mapping:
1. Ask for the source dataset name and target dataset name if not provided
2. Ask if they want REPORT mode (flag unmapped columns) or FIX mode (suggest defaults)
3. Use generate_schema_mapping with the provided parameters
4. Offer to save the mapping with a memorable ID (e.g., "prod_v1", "worldbank_mapping")
5. Explain the results, including:
   - Number of table mappings created
   - Any unmapped columns or issues
   - Validation rules generated
   - Confidence level

**Working with saved mappings:**
- After generating a mapping, ALWAYS ask if they want to save it
- When saving, suggest a meaningful ID based on the dataset names
- Users can load saved mappings later to review, extract parts, or compare
- Use extract_validation_rules to get validation rules for specific tables
- List saved mappings when users ask what's available

**Important:**
- Save mappings proactively so users can reference them later
- When a mapping is generated, the JSON is large - offer to save it with a short ID
- Users can then load it by ID instead of regenerating
- Explain results in business terms, not just technical details

Always be helpful and make it easy to work with multiple mappings in one session.""",
    tools=[
        fetch_table_schema,
        fetch_dataset_schemas,
        generate_schema_mapping,
        save_mapping,
        load_mapping,
        list_mappings,
        extract_validation_rules,
        delete_mapping,
    ],
)

