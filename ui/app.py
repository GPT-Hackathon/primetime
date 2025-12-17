"""Flask Web Dashboard for GPT: Gen Prime Time Pipeline."""

from flask import Flask, render_template, jsonify, request, Response
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import threading
import queue
import uuid
import re
import traceback

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'bigquery_adk_agent', '.env'))

# Set GCP_PROJECT_ID for agents that use it (e.g., validation agent)
if os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT"):
    os.environ["GCP_PROJECT_ID"] = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")

# BigQuery and GCS imports
try:
    from google.cloud import bigquery
    from google.cloud import storage
    from google.api_core.exceptions import NotFound
    BIGQUERY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: BigQuery/GCS not available: {e}")
    BIGQUERY_AVAILABLE = False

app = Flask(__name__)

# Global state for pipeline execution
pipeline_state = {
    'status': 'idle',  # idle, running, completed, error
    'current_step': None,
    'progress': 0,
    'results': {},
    'logs': [],
    'start_time': None,
    'end_time': None
}

# Session state for datasets
session_state = {
    'session_id': None,
    'staging_dataset': None,
    'target_dataset': None,
    'tables': [],
    'data_cache': {},
    'source_files': [],
    'target_files': [],
    'status': 'idle',
    'error': None
}

# Queue for server-sent events
event_queue = queue.Queue()

# ADK Agent state - persistent across requests
agent_state = {
    'runner': None,
    'session_service': None,
    'session_id': None,
    'user_id': 'ui_user',
    'initialized': False,
    'event_loop': None
}


def get_project_id():
    """Get GCP project ID from environment."""
    project_id = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("PROJECT_ID or GOOGLE_CLOUD_PROJECT environment variable not set.")
    return project_id


def log_event(message, level='info'):
    """Log an event and send to UI."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'message': message
    }
    pipeline_state['logs'].append(log_entry)
    try:
        event_queue.put_nowait(json.dumps(log_entry))
    except:
        pass
    print(f"[{timestamp}] [{level.upper()}] {message}")


def parse_gcs_path(path):
    """Parse a GCS path into bucket and prefix.

    Accepts formats:
    - gs://bucket/path/to/files
    - bucket/path/to/files (assumes gs://)
    """
    # Remove gs:// prefix if present
    if path.startswith('gs://'):
        path = path[5:]

    # Split into bucket and prefix
    parts = path.split('/', 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''

    # Remove wildcard from prefix for listing
    if prefix.endswith('/*.csv'):
        prefix = prefix[:-6]
    elif prefix.endswith('/*.sql'):
        prefix = prefix[:-6]
    elif prefix.endswith('/*'):
        prefix = prefix[:-2]

    return bucket_name, prefix


def list_gcs_files(bucket_name, prefix, extension=None):
    """List files in GCS bucket with optional extension filter."""
    try:
        project_id = get_project_id()
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)

        blobs = bucket.list_blobs(prefix=prefix)
        files = []

        for blob in blobs:
            if extension:
                if blob.name.endswith(extension):
                    files.append(f"gs://{bucket_name}/{blob.name}")
            else:
                files.append(f"gs://{bucket_name}/{blob.name}")

        return files
    except Exception as e:
        log_event(f"Error listing GCS files: {e}", 'error')
        return []


def download_gcs_file(gcs_uri):
    """Download a file from GCS and return its content."""
    try:
        project_id = get_project_id()
        storage_client = storage.Client(project=project_id)

        # Parse gs://bucket/path
        if gcs_uri.startswith('gs://'):
            gcs_uri = gcs_uri[5:]

        parts = gcs_uri.split('/', 1)
        bucket_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else ''

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        return blob.download_as_text()
    except Exception as e:
        log_event(f"Error downloading {gcs_uri}: {e}", 'error')
        return None


def create_dataset(client, project_id, dataset_name):
    """Create a BigQuery dataset if it doesn't exist."""
    dataset_id = f"{project_id}.{dataset_name}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    try:
        dataset = client.create_dataset(dataset, exists_ok=True)
        return True
    except Exception as e:
        log_event(f"Error creating dataset {dataset_name}: {e}", 'error')
        return False


def delete_dataset(client, project_id, dataset_name):
    """Delete a BigQuery dataset and all its tables."""
    dataset_id = f"{project_id}.{dataset_name}"
    try:
        client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
        return True
    except Exception as e:
        log_event(f"Error deleting dataset {dataset_name}: {e}", 'error')
        return False


def load_csv_from_gcs_to_bigquery(client, project_id, dataset_name, gcs_uri):
    """Load a CSV file from GCS into BigQuery table."""
    # Extract table name from GCS path
    file_name = gcs_uri.split('/')[-1]
    table_name = file_name.replace('.csv', '')
    table_id = f"{project_id}.{dataset_name}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    load_job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    load_job.result()  # Wait for job to complete

    table = client.get_table(table_id)
    return {
        'table_name': table_name,
        'rows': table.num_rows,
        'columns': len(table.schema)
    }


def parse_ddl_and_create_table(client, project_id, dataset_name, ddl_content, file_name):
    """Parse DDL content and create the table in BigQuery."""
    # Replace placeholder project.dataset with actual values
    ddl_content = re.sub(
        r'`[^`]+\.[^`]+\.([^`]+)`',
        f'`{project_id}.{dataset_name}.\\1`',
        ddl_content
    )
    ddl_content = re.sub(
        r'project\.dataset\.(\w+)',
        f'{project_id}.{dataset_name}.\\1',
        ddl_content
    )

    # Execute the DDL
    try:
        query_job = client.query(ddl_content)
        query_job.result()

        # Extract table name from DDL
        match = re.search(r'CREATE\s+TABLE\s+`?[^`\s]+\.([^`\s\(]+)`?', ddl_content, re.IGNORECASE)
        if match:
            table_name = match.group(1)
        else:
            table_name = file_name.replace('.sql', '')

        return {
            'table_name': table_name,
            'status': 'created'
        }
    except Exception as e:
        return {
            'table_name': file_name.replace('.sql', ''),
            'status': 'error',
            'error': str(e)
        }


def load_data_async(source_path, target_path):
    """Load data into BigQuery in background thread."""
    global session_state

    try:
        log_event("Starting data load process...", 'info')

        # Generate session ID
        session_id = str(uuid.uuid4())[:8]
        staging_dataset = f"staging_dataset_{session_id}"
        target_dataset = f"target_dataset_{session_id}"

        log_event(f"Session ID: {session_id}", 'info')
        log_event(f"Staging dataset: {staging_dataset}", 'info')
        log_event(f"Target dataset: {target_dataset}", 'info')

        # Update session state
        session_state['session_id'] = session_id
        session_state['staging_dataset'] = staging_dataset
        session_state['target_dataset'] = target_dataset
        session_state['error'] = None

        if not BIGQUERY_AVAILABLE:
            log_event("BigQuery not available - cannot load data", 'error')
            session_state['status'] = 'error'
            session_state['error'] = 'BigQuery client not available'
            return

        project_id = get_project_id()
        log_event(f"Project ID: {project_id}", 'info')

        bq_client = bigquery.Client(project=project_id)

        # Parse GCS paths
        source_bucket, source_prefix = parse_gcs_path(source_path)
        target_bucket, target_prefix = parse_gcs_path(target_path)

        log_event(f"Source bucket: {source_bucket}, prefix: {source_prefix}", 'info')
        log_event(f"Target bucket: {target_bucket}, prefix: {target_prefix}", 'info')

        # List source CSV files from GCS
        log_event("Listing source CSV files from GCS...", 'info')
        source_files = list_gcs_files(source_bucket, source_prefix, '.csv')

        if not source_files:
            log_event(f"No CSV files found in gs://{source_bucket}/{source_prefix}", 'error')
            session_state['status'] = 'error'
            session_state['error'] = f'No CSV files found in gs://{source_bucket}/{source_prefix}'
            return

        log_event(f"Found {len(source_files)} source CSV files", 'success')
        for f in source_files:
            log_event(f"  - {f.split('/')[-1]}", 'info')

        # List target DDL files from GCS
        log_event("Listing target DDL files from GCS...", 'info')
        target_files = list_gcs_files(target_bucket, target_prefix, '.sql')
        log_event(f"Found {len(target_files)} target DDL files", 'success')

        session_state['source_files'] = source_files
        session_state['target_files'] = target_files

        # Create datasets
        log_event(f"Creating staging dataset: {staging_dataset}...", 'info')
        if not create_dataset(bq_client, project_id, staging_dataset):
            session_state['status'] = 'error'
            session_state['error'] = f'Failed to create staging dataset'
            return
        log_event("Staging dataset created", 'success')

        log_event(f"Creating target dataset: {target_dataset}...", 'info')
        if not create_dataset(bq_client, project_id, target_dataset):
            session_state['status'] = 'error'
            session_state['error'] = f'Failed to create target dataset'
            return
        log_event("Target dataset created", 'success')

        # Load CSV files into staging dataset
        log_event("Loading CSV files into staging dataset...", 'info')
        tables = []
        total_rows = 0

        for i, gcs_uri in enumerate(source_files, 1):
            file_name = gcs_uri.split('/')[-1]
            log_event(f"  [{i}/{len(source_files)}] Loading {file_name}...", 'info')

            try:
                result = load_csv_from_gcs_to_bigquery(bq_client, project_id, staging_dataset, gcs_uri)
                tables.append(result)
                total_rows += result['rows']
                log_event(f"    Loaded {result['rows']} rows, {result['columns']} columns", 'success')
            except Exception as e:
                log_event(f"    Error loading {file_name}: {e}", 'error')
                log_event(f"    Traceback: {traceback.format_exc()}", 'error')

        session_state['tables'] = tables

        # Create target tables from DDL files
        if target_files:
            log_event("Creating target tables from DDL files...", 'info')
            target_tables = []

            for i, gcs_uri in enumerate(target_files, 1):
                file_name = gcs_uri.split('/')[-1]
                log_event(f"  [{i}/{len(target_files)}] Creating {file_name}...", 'info')

                try:
                    ddl_content = download_gcs_file(gcs_uri)
                    if ddl_content:
                        result = parse_ddl_and_create_table(bq_client, project_id, target_dataset, ddl_content, file_name)
                        target_tables.append(result)
                        if result['status'] == 'created':
                            log_event(f"    Table {result['table_name']} created", 'success')
                        else:
                            log_event(f"    Error: {result.get('error', 'Unknown error')}", 'error')
                    else:
                        log_event(f"    Could not download DDL file", 'error')
                except Exception as e:
                    log_event(f"    Error creating {file_name}: {e}", 'error')

            session_state['target_tables'] = target_tables

        log_event("=" * 50, 'info')
        log_event("Data loading complete!", 'success')
        log_event(f"  Staging: {len(tables)} tables, {total_rows} total rows", 'info')
        log_event(f"  Target: {len(target_files)} tables created", 'info')
        log_event("=" * 50, 'info')

        session_state['status'] = 'loaded'

    except Exception as e:
        error_msg = str(e)
        log_event(f"Load failed: {error_msg}", 'error')
        log_event(f"Traceback: {traceback.format_exc()}", 'error')
        session_state['status'] = 'error'
        session_state['error'] = error_msg


def clear_session():
    """Clear the current session and delete BigQuery datasets."""
    global session_state, pipeline_state, agent_state

    if BIGQUERY_AVAILABLE and session_state.get('session_id'):
        try:
            project_id = get_project_id()
            client = bigquery.Client(project=project_id)

            # Delete staging dataset
            if session_state.get('staging_dataset'):
                log_event(f"Deleting staging dataset: {session_state['staging_dataset']}", 'info')
                delete_dataset(client, project_id, session_state['staging_dataset'])
                log_event("Staging dataset deleted", 'success')

            # Delete target dataset
            if session_state.get('target_dataset'):
                log_event(f"Deleting target dataset: {session_state['target_dataset']}", 'info')
                delete_dataset(client, project_id, session_state['target_dataset'])
                log_event("Target dataset deleted", 'success')

        except Exception as e:
            log_event(f"Error during cleanup: {e}", 'error')

    # Reset agent state for new session
    reset_agent()

    # Reset session state
    session_state['session_id'] = None
    session_state['staging_dataset'] = None
    session_state['target_dataset'] = None
    session_state['tables'] = []
    session_state['data_cache'] = {}
    session_state['source_files'] = []
    session_state['target_files'] = []
    session_state['status'] = 'idle'
    session_state['error'] = None

    # Reset pipeline state
    pipeline_state['status'] = 'idle'
    pipeline_state['current_step'] = None
    pipeline_state['progress'] = 0
    pipeline_state['results'] = {}
    pipeline_state['logs'] = []


@app.route('/')
def index():
    """Render main dashboard."""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """Get current pipeline status."""
    return jsonify({
        **pipeline_state,
        'session': {
            'session_id': session_state.get('session_id'),
            'staging_dataset': session_state.get('staging_dataset'),
            'target_dataset': session_state.get('target_dataset'),
            'status': session_state.get('status', 'idle'),
            'error': session_state.get('error')
        }
    })


@app.route('/api/load', methods=['POST'])
def load_data():
    """Load source data into staging tables."""
    global session_state

    try:
        data = request.json
        source_path = data.get('source_files', '')
        target_path = data.get('target_ddls', '')

        log_event(f"Received load request", 'info')
        log_event(f"  Source: {source_path}", 'info')
        log_event(f"  Target: {target_path}", 'info')

        if not source_path:
            return jsonify({'error': 'source_files path is required'}), 400

        # Clear logs for fresh start
        pipeline_state['logs'] = []

        # Clear existing session if any
        if session_state.get('session_id'):
            log_event("Clearing existing session...", 'info')
            clear_session()

        session_state['status'] = 'loading'

        # Run load in background thread
        thread = threading.Thread(
            target=load_data_async,
            args=(source_path, target_path)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'message': 'Load started',
            'status': 'loading'
        })

    except Exception as e:
        error_msg = str(e)
        log_event(f"Load request failed: {error_msg}", 'error')
        log_event(f"Traceback: {traceback.format_exc()}", 'error')
        return jsonify({'error': error_msg}), 500


@app.route('/api/load/status')
def load_status():
    """Get current load status."""
    return jsonify({
        'status': session_state.get('status', 'idle'),
        'session_id': session_state.get('session_id'),
        'staging_dataset': session_state.get('staging_dataset'),
        'target_dataset': session_state.get('target_dataset'),
        'tables': session_state.get('tables', []),
        'target_tables': session_state.get('target_tables', []),
        'source_count': len(session_state.get('source_files', [])),
        'target_count': len(session_state.get('target_files', [])),
        'row_count': sum(t.get('rows', 0) for t in session_state.get('tables', [])),
        'error': session_state.get('error')
    })


@app.route('/api/preview/<table_name>')
def preview_table(table_name):
    """Get paginated preview of table data from BigQuery."""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))
        dataset_type = request.args.get('dataset_type', 'staging')  # 'staging' or 'target'

        if not BIGQUERY_AVAILABLE:
            return jsonify({'error': 'BigQuery not available'}), 404

        # Determine which dataset to use
        if dataset_type == 'target':
            dataset_name = session_state.get('target_dataset')
        else:
            dataset_name = session_state.get('staging_dataset')

        if not dataset_name:
            return jsonify({'error': f'No {dataset_type} dataset loaded'}), 404

        project_id = get_project_id()
        client = bigquery.Client(project=project_id)

        table_id = f"{project_id}.{dataset_name}.{table_name}"

        # Get total count
        count_query = f"SELECT COUNT(*) as cnt FROM `{table_id}`"
        count_result = client.query(count_query).result()
        total_rows = list(count_result)[0].cnt

        # Get paginated data
        offset = (page - 1) * page_size
        query = f"SELECT * FROM `{table_id}` LIMIT {page_size} OFFSET {offset}"
        result = client.query(query).result()

        # Convert to list of dicts
        rows = []
        columns = []
        for row in result:
            if not columns:
                columns = list(row.keys())
            rows.append(dict(row))

        return jsonify({
            'columns': columns,
            'rows': rows,
            'total_rows': total_rows,
            'page': page,
            'page_size': page_size,
            'dataset_type': dataset_type,
            'dataset_name': dataset_name
        })

    except Exception as e:
        log_event(f"Preview error: {e}", 'error')
        return jsonify({'error': str(e)}), 500


@app.route('/api/run', methods=['POST'])
def run_pipeline():
    """Start pipeline execution - initializes the agent session."""
    global pipeline_state

    if pipeline_state['status'] == 'running':
        return jsonify({'error': 'Pipeline already running'}), 400

    if not session_state.get('session_id'):
        return jsonify({'error': 'No data loaded. Please load data first.'}), 400

    try:
        data = request.json or {}
        mode = data.get('mode', 'fix')

        staging_dataset = session_state.get('staging_dataset')
        target_dataset = session_state.get('target_dataset')

        # Reset agent for fresh pipeline run
        reset_agent()

        # Initialize pipeline state
        pipeline_state['status'] = 'running'
        pipeline_state['current_step'] = 'initializing'
        pipeline_state['progress'] = 0
        pipeline_state['results'] = {}
        pipeline_state['start_time'] = datetime.now().isoformat()
        pipeline_state['agent_history'] = []
        pipeline_state['awaiting_continue'] = False

        log_event("=" * 50, 'info')
        log_event("Starting Pipeline Execution", 'info')
        log_event("=" * 50, 'info')
        log_event(f"Staging Dataset: {staging_dataset}", 'info')
        log_event(f"Target Dataset: {target_dataset}", 'info')
        log_event(f"Mode: {mode.upper()}", 'info')

        # Store mode in pipeline state for later steps
        pipeline_state['mode'] = mode.upper()

        # Create the initial prompt for the agent
        initial_prompt = f"""This is a new session for data integration pipeline.

Source/Staging Dataset: {staging_dataset}
Target Dataset: {target_dataset}
Mode: {mode.upper()}

IMPORTANT: Execute in "{mode.upper()}" mode:
- REPORT mode: Only analyze and report issues, do not make any changes
- FIX mode: Analyze issues AND apply corrections/transformations

Please execute the data integration workflow step by step. After each step, stop and provide results in JSON format with the following structure:
{{
    "step": "<step_name>",
    "status": "completed" | "error" | "pending",
    "message": "<human readable message>",
    "details": {{ <step specific details> }},
    "schema_mapping_result": {{ <COMPLETE schema mapping output with all table mappings, column mappings, confidence scores> }},
    "next_action": "<description of next step>",
    "requires_confirmation": true | false
}}

CRITICAL: The "schema_mapping_result" field MUST contain the COMPLETE schema mapping output with this structure:
{{
    "status": "success",
    "mapping": {{
        "metadata": {{
            "source_dataset": "<source_dataset>",
            "target_dataset": "<target_dataset>",
            "mode": "<mode>",
            "confidence": "high|medium|low",
            "generated_at": "<timestamp>"
        }},
        "mappings": [
            {{
                "source_table": "<fully qualified source table name>",
                "target_table": "<fully qualified target table name>",
                "match_confidence": <0.0 to 1.0>,
                "column_mappings": [
                    {{
                        "source_column": "<source column name>",
                        "target_column": "<target column name>",
                        "source_type": "<data type>",
                        "target_type": "<data type>",
                        "type_conversion_needed": true|false,
                        "transformation": "<transformation expression or null>",
                        "notes": "<any notes>"
                    }}
                ],
                "unmapped_source_columns": ["<list of unmapped source columns>"],
                "unmapped_target_columns": ["<list of unmapped target columns>"],
                "mapping_errors": [
                    {{
                        "error_type": "<error type>",
                        "target_column": "<column>",
                        "severity": "WARNING|ERROR",
                        "message": "<error message>"
                    }}
                ]
            }}
        ]
    }},
    "metadata": {{
        "source_dataset": "<source>",
        "target_dataset": "<target>",
        "mode": "<mode>",
        "num_mappings": <count>,
        "confidence": "high|medium|low"
    }}
}}

Start with Step 1: Generate schema mapping between the staging and target datasets.
Call generate_schema_mapping with:
- source_dataset: "{staging_dataset}"
- target_dataset: "{target_dataset}"
- mode: "{mode.upper()}"

Please proceed with the first step now and include the COMPLETE schema_mapping_result in your response."""

        pipeline_state['current_prompt'] = initial_prompt
        pipeline_state['current_step'] = 'schema_mapping'
        pipeline_state['progress'] = 10

        log_event("Pipeline initialized. Starting schema mapping...", 'info')

        # Start agent execution in background
        thread = threading.Thread(
            target=run_agent_step_async,
            args=(initial_prompt,)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'status': 'running',
            'message': 'Pipeline started',
            'staging_dataset': staging_dataset,
            'target_dataset': target_dataset,
            'current_step': 'schema_mapping'
        })

    except Exception as e:
        error_msg = str(e)
        log_event(f"Pipeline start failed: {error_msg}", 'error')
        pipeline_state['status'] = 'error'
        return jsonify({'error': error_msg}), 500


def initialize_agent():
    """Initialize the ADK agent with persistent session."""
    global agent_state

    if agent_state['initialized']:
        log_event("Agent already initialized, reusing existing session", 'info')
        return True

    try:
        import asyncio
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        # Import the orchestration agent
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from agents.orchestration.agent import root_agent

        log_event("Initializing ADK Agent...", 'info')

        # Create persistent session service
        agent_state['session_service'] = InMemorySessionService()

        # Create persistent runner
        agent_state['runner'] = Runner(
            agent=root_agent,
            app_name="gpt_pipeline",
            session_service=agent_state['session_service']
        )

        # Generate session ID based on pipeline session
        agent_state['session_id'] = f"pipeline_{session_state.get('session_id', 'default')}"
        agent_state['user_id'] = "ui_user"

        # Create event loop for agent operations
        agent_state['event_loop'] = asyncio.new_event_loop()

        # Create the session
        async def create_session():
            return await agent_state['session_service'].create_session(
                app_name="gpt_pipeline",
                user_id=agent_state['user_id'],
                session_id=agent_state['session_id']
            )

        agent_state['event_loop'].run_until_complete(create_session())

        agent_state['initialized'] = True
        log_event(f"ADK Agent initialized with session: {agent_state['session_id']}", 'success')
        return True

    except ImportError as e:
        log_event(f"ADK Import error: {e}. Using mock agent.", 'warning')
        agent_state['initialized'] = False
        return False
    except Exception as e:
        log_event(f"Agent initialization error: {e}", 'error')
        log_event(f"Traceback: {traceback.format_exc()}", 'error')
        agent_state['initialized'] = False
        return False


def reset_agent():
    """Reset the agent state for a new pipeline run."""
    global agent_state

    try:
        if agent_state.get('event_loop') and not agent_state['event_loop'].is_closed():
            try:
                agent_state['event_loop'].close()
            except Exception as e:
                log_event(f"Warning: Error closing event loop: {e}", 'warning')
    except Exception as e:
        log_event(f"Warning: Error during agent reset: {e}", 'warning')

    agent_state['runner'] = None
    agent_state['session_service'] = None
    agent_state['session_id'] = None
    agent_state['initialized'] = False
    agent_state['event_loop'] = None

    log_event("Agent state reset for new session", 'info')


def run_agent_step_async(prompt):
    """Run agent step asynchronously using persistent session."""
    global pipeline_state, agent_state

    try:
        # Check if we should use real agent or mock
        if agent_state['initialized'] and agent_state['runner']:
            result = run_real_agent_step(prompt)
        else:
            # Try to initialize, fall back to mock if fails
            if initialize_agent():
                result = run_real_agent_step(prompt)
            else:
                result = run_mock_agent_step(prompt)

        # Parse and store result
        pipeline_state['last_result'] = result
        pipeline_state['awaiting_continue'] = True

        log_event("Step completed. Awaiting user confirmation to continue.", 'success')

    except Exception as e:
        error_msg = str(e)
        log_event(f"Agent execution error: {error_msg}", 'error')
        log_event(f"Traceback: {traceback.format_exc()}", 'error')
        pipeline_state['status'] = 'error'
        pipeline_state['error'] = error_msg


def run_real_agent_step(prompt):
    """Execute agent step using the real ADK agent."""
    global pipeline_state, agent_state

    log_event("Executing agent step with ADK...", 'info')

    async def execute():
        from google.genai import types

        content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )

        response_text = ""
        async for event in agent_state['runner'].run_async(
            user_id=agent_state['user_id'],
            session_id=agent_state['session_id'],
            new_message=content
        ):
            # Process events
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
                            # Log partial response (truncate for readability)
                            display_text = part.text[:300] + "..." if len(part.text) > 300 else part.text
                            log_event(f"Agent: {display_text}", 'info')

            # Handle function/tool calls
            if hasattr(event, 'tool_calls') and event.tool_calls:
                for tool_call in event.tool_calls:
                    log_event(f"Calling tool: {tool_call.name}", 'info')

            # Check for function call events
            if hasattr(event, 'function_calls') and event.function_calls:
                for fc in event.function_calls:
                    log_event(f"Function call: {fc.name}", 'info')

        return response_text

    # Run in the persistent event loop
    response_text = agent_state['event_loop'].run_until_complete(execute())

    # Parse the response
    return parse_agent_response(response_text)


def run_mock_agent_step(prompt):
    """Mock agent execution for demo when ADK is not available."""
    global pipeline_state
    import time

    current_step = pipeline_state.get('current_step', 'schema_mapping')

    log_event(f"Running mock agent for step: {current_step}", 'warning')

    # Simulate processing time
    time.sleep(2)

    mode = pipeline_state.get('mode', 'FIX')

    if current_step == 'schema_mapping':
        staging_dataset = session_state.get('staging_dataset', 'staging_dataset_xxx')
        target_dataset = session_state.get('target_dataset', 'target_dataset_xxx')
        project_id = os.environ.get("PROJECT_ID", "project")

        result = {
            "step": "schema_mapping",
            "status": "completed",
            "message": f"Schema mapping completed successfully in {mode} mode. Analyzed source tables and mapped to target schema.",
            "details": {
                "source_dataset": staging_dataset,
                "target_dataset": target_dataset,
                "tables_mapped": len(session_state.get('tables', [])),
                "mode": mode
            },
            "schema_mapping_result": {
                "status": "success",
                "message": None,
                "mapping": {
                    "metadata": {
                        "source_dataset": f"{project_id}.{staging_dataset}",
                        "target_dataset": f"{project_id}.{target_dataset}",
                        "generated_at": datetime.now().isoformat(),
                        "confidence": "high",
                        "mode": mode
                    },
                    "mappings": [
                        {
                            "source_table": f"{project_id}.{staging_dataset}.staging_countries",
                            "target_table": f"{project_id}.{target_dataset}.dim_country",
                            "match_confidence": 0.95,
                            "column_mappings": [
                                {
                                    "source_column": "country_code",
                                    "target_column": "country_key",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Direct mapping of country_code to country_key."
                                },
                                {
                                    "source_column": "country_name",
                                    "target_column": "country_name",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Direct mapping."
                                },
                                {
                                    "source_column": "iso3",
                                    "target_column": "iso3",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Direct mapping."
                                },
                                {
                                    "source_column": "region",
                                    "target_column": "region",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Direct mapping."
                                },
                                {
                                    "source_column": "income_group",
                                    "target_column": "income_group",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Direct mapping."
                                }
                            ],
                            "unmapped_source_columns": [],
                            "unmapped_target_columns": [],
                            "mapping_errors": [],
                            "validation_rules": [
                                {"column": "country_key", "type": "NOT_NULL", "reason": "Target column is REQUIRED."}
                            ],
                            "primary_key": ["country_key"],
                            "uniqueness_constraints": ["country_key"]
                        },
                        {
                            "source_table": f"{project_id}.{staging_dataset}.staging_indicators_meta",
                            "target_table": f"{project_id}.{target_dataset}.dim_indicator",
                            "match_confidence": 0.95,
                            "column_mappings": [
                                {
                                    "source_column": "indicator_code",
                                    "target_column": "indicator_code",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Direct mapping."
                                },
                                {
                                    "source_column": "indicator_name",
                                    "target_column": "indicator_name",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Direct mapping."
                                },
                                {
                                    "source_column": "topic",
                                    "target_column": "topic",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Direct mapping."
                                }
                            ],
                            "unmapped_source_columns": [],
                            "unmapped_target_columns": [],
                            "mapping_errors": [],
                            "validation_rules": [
                                {"column": "indicator_code", "type": "NOT_NULL", "reason": "Target column is REQUIRED."}
                            ],
                            "primary_key": ["indicator_code"],
                            "uniqueness_constraints": ["indicator_code"]
                        },
                        {
                            "source_table": f"{project_id}.{staging_dataset}.staging_gdp",
                            "target_table": f"{project_id}.{target_dataset}.dim_time",
                            "match_confidence": 0.70,
                            "column_mappings": [
                                {
                                    "source_column": "year",
                                    "target_column": "year",
                                    "source_type": "INTEGER",
                                    "target_type": "INTEGER",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Mapping from staging_gdp.year as a representative source for years."
                                },
                                {
                                    "source_column": "GENERATED",
                                    "target_column": "year_key",
                                    "source_type": "EXPRESSION",
                                    "target_type": "STRING",
                                    "type_conversion_needed": True,
                                    "transformation": "CAST(year AS STRING)",
                                    "notes": "Generated year_key from year column for string representation."
                                }
                            ],
                            "unmapped_source_columns": ["country_code", "iso3", "indicator_code", "value"],
                            "unmapped_target_columns": [],
                            "mapping_errors": [],
                            "validation_rules": [
                                {"column": "year", "type": "NOT_NULL", "reason": "Target column is REQUIRED."}
                            ],
                            "primary_key": ["year"],
                            "uniqueness_constraints": ["year"]
                        },
                        {
                            "source_table": f"Multiple Staging Tables (staging_co2_emissions, staging_gdp, staging_life_expectancy, staging_population, staging_poverty_headcount, staging_primary_enrollment)",
                            "target_table": f"{project_id}.{target_dataset}.agg_country_year",
                            "match_confidence": 0.80,
                            "column_mappings": [
                                {
                                    "source_column": "staging_gdp.country_code",
                                    "target_column": "country_key",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Mapped from country_code in staging_gdp, assuming join across sources."
                                },
                                {
                                    "source_column": "staging_gdp.year",
                                    "target_column": "year",
                                    "source_type": "INTEGER",
                                    "target_type": "INTEGER",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Mapped from year in staging_gdp, assuming join across sources."
                                },
                                {
                                    "source_column": "staging_gdp.value",
                                    "target_column": "gdp",
                                    "source_type": "INTEGER",
                                    "target_type": "NUMERIC",
                                    "type_conversion_needed": True,
                                    "transformation": "CAST(staging_gdp.value AS NUMERIC)",
                                    "notes": "GDP value from staging_gdp, requires type conversion."
                                },
                                {
                                    "source_column": "staging_population.value",
                                    "target_column": "population",
                                    "source_type": "INTEGER",
                                    "target_type": "INTEGER",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Population value from staging_population."
                                },
                                {
                                    "source_column": "GENERATED",
                                    "target_column": "gdp_per_capita",
                                    "source_type": "EXPRESSION",
                                    "target_type": "NUMERIC",
                                    "type_conversion_needed": True,
                                    "transformation": "SAFE_DIVIDE(CAST(staging_gdp.value AS NUMERIC), staging_population.value)",
                                    "notes": "Calculated field: GDP divided by Population. Uses SAFE_DIVIDE to handle division by zero."
                                },
                                {
                                    "source_column": "staging_life_expectancy.value",
                                    "target_column": "life_expectancy",
                                    "source_type": "FLOAT",
                                    "target_type": "FLOAT",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Life expectancy value from staging_life_expectancy."
                                },
                                {
                                    "source_column": "staging_co2_emissions.value",
                                    "target_column": "co2_emissions",
                                    "source_type": "INTEGER",
                                    "target_type": "INTEGER",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "CO2 emissions value from staging_co2_emissions."
                                }
                            ],
                            "unmapped_source_columns": [],
                            "unmapped_target_columns": [],
                            "mapping_errors": [],
                            "validation_rules": [],
                            "primary_key": ["country_key", "year"],
                            "uniqueness_constraints": ["country_key", "year"]
                        },
                        {
                            "source_table": f"Multiple Staging Tables (Union of relevant staging tables)",
                            "target_table": f"{project_id}.{target_dataset}.fact_indicator_values",
                            "match_confidence": 0.85,
                            "column_mappings": [
                                {
                                    "source_column": "country_code",
                                    "target_column": "country_key",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Mapped from country_code across all indicator staging tables."
                                },
                                {
                                    "source_column": "year",
                                    "target_column": "year",
                                    "source_type": "INTEGER",
                                    "target_type": "INTEGER",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Mapped from year across all indicator staging tables."
                                },
                                {
                                    "source_column": "indicator_code",
                                    "target_column": "indicator_code",
                                    "source_type": "STRING",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": None,
                                    "notes": "Mapped from indicator_code across all indicator staging tables."
                                },
                                {
                                    "source_column": "value",
                                    "target_column": "numeric_value",
                                    "source_type": "INTEGER/FLOAT",
                                    "target_type": "NUMERIC",
                                    "type_conversion_needed": True,
                                    "transformation": "CAST(value AS NUMERIC)",
                                    "notes": "Generic value column from all indicator staging tables, requires conversion to NUMERIC."
                                },
                                {
                                    "source_column": "GENERATED",
                                    "target_column": "data_source",
                                    "source_type": "EXPRESSION",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": "'source_table_name'",
                                    "notes": "Generated to indicate the original staging table for the indicator value."
                                },
                                {
                                    "source_column": "GENERATED",
                                    "target_column": "loaded_at",
                                    "source_type": "EXPRESSION",
                                    "target_type": "TIMESTAMP",
                                    "type_conversion_needed": False,
                                    "transformation": "CURRENT_TIMESTAMP()",
                                    "notes": "Auto-generated timestamp for audit purposes."
                                }
                            ],
                            "unmapped_source_columns": [],
                            "unmapped_target_columns": [],
                            "mapping_errors": [],
                            "validation_rules": [],
                            "primary_key": ["country_key", "year", "indicator_code", "data_source"],
                            "uniqueness_constraints": ["country_key", "year", "indicator_code", "data_source"]
                        },
                        {
                            "source_table": "UNMAPPED",
                            "target_table": f"{project_id}.{target_dataset}.dim_risk_rating",
                            "match_confidence": 0.1,
                            "column_mappings": [
                                {
                                    "source_column": "GENERATED",
                                    "target_column": "rating_id",
                                    "source_type": "EXPRESSION",
                                    "target_type": "INTEGER",
                                    "type_conversion_needed": False,
                                    "transformation": "DEFAULT: 0",
                                    "notes": "No source column found. Defaulting to 0 for INTEGER type."
                                },
                                {
                                    "source_column": "GENERATED",
                                    "target_column": "loan_id",
                                    "source_type": "EXPRESSION",
                                    "target_type": "INTEGER",
                                    "type_conversion_needed": False,
                                    "transformation": "DEFAULT: 0",
                                    "notes": "No source column found. Defaulting to 0 for INTEGER type."
                                },
                                {
                                    "source_column": "GENERATED",
                                    "target_column": "rating_agency",
                                    "source_type": "EXPRESSION",
                                    "target_type": "STRING",
                                    "type_conversion_needed": False,
                                    "transformation": "DEFAULT: 'UNKNOWN'",
                                    "notes": "No source column found. Defaulting to 'UNKNOWN' for STRING type."
                                }
                            ],
                            "unmapped_source_columns": [],
                            "unmapped_target_columns": [],
                            "mapping_errors": [
                                {
                                    "error_type": "NO_SOURCE_TABLE_MATCH",
                                    "target_table": f"{project_id}.{target_dataset}.dim_risk_rating",
                                    "severity": "WARNING",
                                    "message": "No direct source table found for dim_risk_rating. All columns generated with default values."
                                }
                            ],
                            "validation_rules": [],
                            "primary_key": ["rating_id"],
                            "uniqueness_constraints": ["rating_id"]
                        },
                        {
                            "source_table": "UNMAPPED",
                            "target_table": f"{project_id}.{target_dataset}.fact_loan_snapshot",
                            "match_confidence": 0.1,
                            "column_mappings": [
                                {
                                    "source_column": "GENERATED",
                                    "target_column": "loan_id",
                                    "source_type": "EXPRESSION",
                                    "target_type": "INTEGER",
                                    "type_conversion_needed": False,
                                    "transformation": "DEFAULT: 0",
                                    "notes": "No source column found. Defaulting to 0 for INTEGER type."
                                },
                                {
                                    "source_column": "GENERATED",
                                    "target_column": "snapshot_date",
                                    "source_type": "EXPRESSION",
                                    "target_type": "DATE",
                                    "type_conversion_needed": False,
                                    "transformation": "DEFAULT: CURRENT_DATE()",
                                    "notes": "No source column found. Defaulting to current date for DATE type."
                                }
                            ],
                            "unmapped_source_columns": [],
                            "unmapped_target_columns": [],
                            "mapping_errors": [
                                {
                                    "error_type": "NO_SOURCE_TABLE_MATCH",
                                    "target_table": f"{project_id}.{target_dataset}.fact_loan_snapshot",
                                    "severity": "WARNING",
                                    "message": "No direct source table found for fact_loan_snapshot. All columns generated with default values."
                                }
                            ],
                            "validation_rules": [],
                            "primary_key": ["loan_id", "snapshot_date"],
                            "uniqueness_constraints": ["loan_id", "snapshot_date"]
                        }
                    ]
                },
                "metadata": {
                    "source_dataset": staging_dataset,
                    "target_dataset": target_dataset,
                    "mode": mode,
                    "num_mappings": 7,
                    "confidence": "high"
                }
            },
            "next_action": "Validate data quality in staging tables",
            "requires_confirmation": True
        }
        pipeline_state['progress'] = 40

    elif current_step == 'validation':
        staging_dataset = session_state.get('staging_dataset', 'staging_dataset_xxx')
        project_id = os.environ.get("PROJECT_ID", "project")

        result = {
            "step": "data_validation",
            "status": "completed",
            "message": f"Data validation completed in {mode} mode. Checked {session_state.get('row_count', 0)} rows across {len(session_state.get('tables', []))} tables. Found 8 errors and 14 warnings.",
            "details": {
                "tables_validated": len(session_state.get('tables', [])),
                "total_rows_checked": session_state.get('row_count', 0),
                "total_errors": 8,
                "total_warnings": 14,
                "mode": mode
            },
            "validation_result_json": {
                "validation_summary": {
                    "total_tables_validated": len(session_state.get('tables', [])),
                    "total_errors": 8,
                    "total_warnings": 14,
                    "tables_with_errors": 4,
                    "validation_timestamp": datetime.now().isoformat(),
                    "mode": mode,
                    "run_id": f"val_{session_state.get('session_id', 'default')}"
                },
                "validation_errors": [
                    {
                        "table_name": f"{project_id}.{staging_dataset}.staging_countries",
                        "error_type": "UNIQUENESS",
                        "failed_column": "country_code",
                        "error_count": 2,
                        "severity": "ERROR",
                        "sql_query": f"SELECT COUNT(*) as error_count FROM (SELECT country_code, COUNT(*) as cnt FROM `{project_id}.{staging_dataset}.staging_countries` GROUP BY country_code HAVING COUNT(*) > 1)",
                        "error_message": "Duplicate rows found for primary key (country_code). 2 duplicate entries detected.",
                        "sample_values": ["USA", "CHN"]
                    },
                    {
                        "table_name": f"{project_id}.{staging_dataset}.staging_gdp",
                        "error_type": "NOT_NULL",
                        "failed_column": "value",
                        "error_count": 15,
                        "severity": "WARNING",
                        "sql_query": f"SELECT COUNT(*) as error_count FROM `{project_id}.{staging_dataset}.staging_gdp` WHERE value IS NULL",
                        "error_message": "NULL values found in column 'value'. 15 rows affected.",
                        "sample_values": None
                    },
                    {
                        "table_name": f"{project_id}.{staging_dataset}.staging_gdp",
                        "error_type": "UNIQUENESS",
                        "failed_column": "country_code,year",
                        "error_count": 3,
                        "severity": "ERROR",
                        "sql_query": f"SELECT COUNT(*) as error_count FROM (SELECT country_code, year, COUNT(*) as cnt FROM `{project_id}.{staging_dataset}.staging_gdp` GROUP BY country_code, year HAVING COUNT(*) > 1)",
                        "error_message": "Duplicate rows found for composite key (country_code, year). 3 duplicate entries detected.",
                        "sample_values": ["USA,2020", "IND,2019", "BRA,2021"]
                    },
                    {
                        "table_name": f"{project_id}.{staging_dataset}.staging_population",
                        "error_type": "DATA_TYPE",
                        "failed_column": "year",
                        "error_count": 5,
                        "severity": "WARNING",
                        "sql_query": f"SELECT COUNT(*) as error_count FROM `{project_id}.{staging_dataset}.staging_population` WHERE SAFE_CAST(year AS INT64) IS NULL AND year IS NOT NULL",
                        "error_message": "Invalid data type in column 'year'. Expected INTEGER but found non-numeric values.",
                        "sample_values": ["20-21", "2k20", "TBD", "N/A", ""]
                    },
                    {
                        "table_name": f"{project_id}.{staging_dataset}.staging_life_expectancy",
                        "error_type": "NOT_NULL",
                        "failed_column": "indicator_code",
                        "error_count": 8,
                        "severity": "WARNING",
                        "sql_query": f"SELECT COUNT(*) as error_count FROM `{project_id}.{staging_dataset}.staging_life_expectancy` WHERE indicator_code IS NULL",
                        "error_message": "NULL values found in required column 'indicator_code'. 8 rows affected.",
                        "sample_values": None
                    },
                    {
                        "table_name": f"{project_id}.{staging_dataset}.staging_co2_emissions",
                        "error_type": "REFERENTIAL_INTEGRITY",
                        "failed_column": "country_code",
                        "error_count": 3,
                        "severity": "ERROR",
                        "sql_query": f"SELECT COUNT(*) as error_count FROM `{project_id}.{staging_dataset}.staging_co2_emissions` e LEFT JOIN `{project_id}.{staging_dataset}.staging_countries` c ON e.country_code = c.country_code WHERE c.country_code IS NULL",
                        "error_message": "Referential integrity violation: 3 rows in staging_co2_emissions reference non-existent country_code in staging_countries.",
                        "sample_values": ["XYZ", "ABC", "XXX"]
                    },
                    {
                        "table_name": f"{project_id}.{staging_dataset}.staging_indicators_meta",
                        "error_type": "FORMAT",
                        "failed_column": "indicator_code",
                        "error_count": 2,
                        "severity": "WARNING",
                        "sql_query": f"SELECT COUNT(*) as error_count FROM `{project_id}.{staging_dataset}.staging_indicators_meta` WHERE NOT REGEXP_CONTAINS(indicator_code, r'^[A-Z]{{2,3}}\\.[A-Z]+')",
                        "error_message": "Invalid format in column 'indicator_code'. Expected pattern: XX.XXXXX (e.g., SP.POP.TOTL).",
                        "sample_values": ["pop_total", "gdp-per-cap"]
                    },
                    {
                        "table_name": f"{project_id}.{staging_dataset}.staging_poverty_headcount",
                        "error_type": "NOT_NULL",
                        "failed_column": "value",
                        "error_count": 12,
                        "severity": "WARNING",
                        "sql_query": f"SELECT COUNT(*) as error_count FROM `{project_id}.{staging_dataset}.staging_poverty_headcount` WHERE value IS NULL",
                        "error_message": "NULL values found in column 'value'. 12 rows affected - poverty data missing for several country-year combinations.",
                        "sample_values": None
                    }
                ]
            },
            "next_action": "Review validation errors and proceed with ETL transformation",
            "requires_confirmation": True
        }
        pipeline_state['progress'] = 70

    elif current_step == 'etl':
        result = {
            "step": "etl_transformation",
            "status": "completed",
            "message": f"ETL transformation completed successfully in {mode} mode. Data loaded into target tables.",
            "details": {
                "rows_transformed": session_state.get('row_count', 0),
                "tables_loaded": 5,
                "target_dataset": session_state.get('target_dataset'),
                "mode": mode
            },
            "result_json": {
                "etl_results": {
                    "run_id": f"etl_{session_state.get('session_id', 'default')}",
                    "mode": mode,
                    "timestamp": datetime.now().isoformat(),
                    "summary": {
                        "total_source_rows": session_state.get('row_count', 0),
                        "total_target_rows": session_state.get('row_count', 0) - 22,
                        "rows_transformed": session_state.get('row_count', 0),
                        "rows_rejected": 2,
                        "tables_loaded": 5
                    },
                    "table_results": [
                        {"table": "dim_country", "rows_inserted": 58, "rows_updated": 0, "status": "success"},
                        {"table": "dim_indicator", "rows_inserted": 8, "rows_updated": 0, "status": "success"},
                        {"table": "fact_indicator_values", "rows_inserted": 2500, "rows_updated": 0, "status": "success"}
                    ],
                    "transformations_applied": [
                        {"name": "Country code standardization", "rows_affected": 60},
                        {"name": "Date format normalization", "rows_affected": 5},
                        {"name": "NULL value handling", "rows_affected": 15},
                        {"name": "Indicator value type casting", "rows_affected": 2500}
                    ]
                }
            },
            "next_action": "Pipeline complete",
            "requires_confirmation": False
        }
        pipeline_state['progress'] = 100
        pipeline_state['status'] = 'completed'
        pipeline_state['awaiting_continue'] = False

    else:
        result = {
            "step": "complete",
            "status": "completed",
            "message": "Pipeline execution completed successfully!",
            "details": {
                "total_steps": 3,
                "staging_dataset": session_state.get('staging_dataset'),
                "target_dataset": session_state.get('target_dataset')
            },
            "next_action": "None",
            "requires_confirmation": False
        }
        pipeline_state['progress'] = 100
        pipeline_state['status'] = 'completed'
        pipeline_state['awaiting_continue'] = False

    pipeline_state['last_result'] = result
    return result


def parse_agent_response(response_text):
    """Parse agent response and extract JSON result."""
    global pipeline_state

    try:
        # Look for JSON in the response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group())

            # Update progress based on step
            step = result.get('step', '')
            if 'schema' in step.lower() or 'mapping' in step.lower():
                pipeline_state['progress'] = 40
                pipeline_state['current_step'] = 'schema_mapping'
            elif 'valid' in step.lower():
                pipeline_state['progress'] = 70
                pipeline_state['current_step'] = 'validation'
            elif 'etl' in step.lower() or 'transform' in step.lower():
                pipeline_state['progress'] = 90
                pipeline_state['current_step'] = 'etl'
            elif 'complete' in step.lower() or 'finish' in step.lower():
                pipeline_state['progress'] = 100
                pipeline_state['current_step'] = 'completed'
                pipeline_state['status'] = 'completed'

            return result
        else:
            # No JSON found, wrap the response
            return {
                'step': pipeline_state.get('current_step', 'unknown'),
                'status': 'completed',
                'message': response_text[:500] if len(response_text) > 500 else response_text,
                'details': {'raw_response': response_text},
                'requires_confirmation': True
            }
    except json.JSONDecodeError:
        return {
            'step': pipeline_state.get('current_step', 'unknown'),
            'status': 'completed',
            'message': response_text[:500] if len(response_text) > 500 else response_text,
            'details': {'raw_response': response_text},
            'requires_confirmation': True
        }


@app.route('/api/pipeline/continue', methods=['POST'])
def continue_pipeline():
    """Continue pipeline execution after user confirmation."""
    global pipeline_state

    if pipeline_state['status'] != 'running':
        return jsonify({'error': 'Pipeline is not running'}), 400

    if not pipeline_state.get('awaiting_continue'):
        return jsonify({'error': 'Pipeline is not awaiting confirmation'}), 400

    try:
        data = request.json or {}
        action = data.get('action', 'continue')  # 'continue' or 'stop'

        if action == 'stop':
            pipeline_state['status'] = 'stopped'
            pipeline_state['awaiting_continue'] = False
            log_event("Pipeline stopped by user", 'warning')
            return jsonify({'status': 'stopped', 'message': 'Pipeline stopped'})

        # Determine next step
        current_step = pipeline_state.get('current_step', 'schema_mapping')
        last_result = pipeline_state.get('last_result', {})

        # Get mode from pipeline state
        mode = pipeline_state.get('mode', 'FIX')

        if current_step == 'schema_mapping':
            next_step = 'validation'
            next_prompt = f"""Continue with Step 2: Data Validation

Mode: {mode}
Using the schema mapping from the previous step, validate the data quality in the staging dataset {session_state.get('staging_dataset')}.

Call validate_data with:
- mapping_id: Use the mapping_id from the previous step
- mode: "{mode}"

Check for:
1. NULL values in required fields
2. Data type mismatches
3. Referential integrity issues
4. Duplicate records
5. Uniqueness constraints

IMPORTANT: Provide results in JSON format with the following structure:
{{
    "step": "data_validation",
    "status": "completed" | "error",
    "message": "<summary of validation results>",
    "details": {{ <validation summary stats> }},
    "validation_result_json": {{
        "validation_summary": {{
            "total_tables_validated": <count>,
            "total_errors": <count>,
            "total_warnings": <count>,
            "tables_with_errors": <count>,
            "validation_timestamp": "<timestamp>"
        }},
        "validation_errors": [
            {{
                "table_name": "<table name>",
                "error_type": "UNIQUENESS" | "NOT_NULL" | "DATA_TYPE" | "REFERENTIAL_INTEGRITY" | "FORMAT",
                "failed_column": "<column name or comma-separated columns>",
                "error_count": <number of errors>,
                "severity": "ERROR" | "WARNING",
                "sql_query": "<SQL query used for validation>",
                "error_message": "<human readable error message>",
                "sample_values": [<list of sample bad values>]
            }}
        ]
    }},
    "next_action": "<next step>",
    "requires_confirmation": true
}}

Include the COMPLETE validation results in the "validation_result_json" field with all errors found."""
            pipeline_state['current_step'] = 'validation'

        elif current_step == 'validation':
            next_step = 'etl'
            next_prompt = f"""Continue with Step 3: ETL Transformation

Mode: {mode}
Based on the schema mapping and validation results, proceed with the ETL transformation:
1. Apply data cleansing rules based on validation errors
2. Transform data to match target schema
3. Load data into target dataset {session_state.get('target_dataset')}

IMPORTANT: Provide results in JSON format with the following structure:
{{
    "step": "etl_transformation",
    "status": "completed" | "error",
    "message": "<summary of ETL results>",
    "details": {{ <ETL summary stats> }},
    "result_json": {{ <complete etl_results.json with transformation details, row counts, success/failure per table> }},
    "next_action": "Pipeline complete",
    "requires_confirmation": false
}}

Include the COMPLETE ETL results in the "result_json" field."""
            pipeline_state['current_step'] = 'etl'

        else:
            # Pipeline complete
            pipeline_state['status'] = 'completed'
            pipeline_state['progress'] = 100
            pipeline_state['awaiting_continue'] = False
            log_event("Pipeline completed successfully!", 'success')
            return jsonify({
                'status': 'completed',
                'message': 'Pipeline completed successfully'
            })

        pipeline_state['awaiting_continue'] = False
        log_event(f"Continuing to step: {next_step}", 'info')

        # Run next step in background
        thread = threading.Thread(
            target=run_agent_step_async,
            args=(next_prompt,)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'status': 'running',
            'current_step': next_step,
            'message': f'Continuing with {next_step}'
        })

    except Exception as e:
        error_msg = str(e)
        log_event(f"Continue failed: {error_msg}", 'error')
        return jsonify({'error': error_msg}), 500


@app.route('/api/pipeline/status')
def pipeline_status():
    """Get current pipeline execution status."""
    return jsonify({
        'status': pipeline_state.get('status', 'idle'),
        'current_step': pipeline_state.get('current_step'),
        'progress': pipeline_state.get('progress', 0),
        'awaiting_continue': pipeline_state.get('awaiting_continue', False),
        'last_result': pipeline_state.get('last_result'),
        'error': pipeline_state.get('error')
    })


@app.route('/api/pipeline/rerun', methods=['POST'])
def rerun_pipeline_step():
    """Re-run the current pipeline step with additional user instructions."""
    global pipeline_state

    if pipeline_state['status'] != 'running':
        return jsonify({'error': 'Pipeline is not running'}), 400

    if not pipeline_state.get('awaiting_continue'):
        return jsonify({'error': 'Pipeline is not awaiting confirmation'}), 400

    try:
        data = request.json or {}
        step = data.get('step', pipeline_state.get('current_step', 'schema_mapping'))
        user_instructions = data.get('instructions', '')

        log_event(f"Re-running step: {step} with additional instructions", 'info')

        # Build the re-run prompt
        mode = pipeline_state.get('mode', 'FIX')
        staging_dataset = session_state.get('staging_dataset', '')
        target_dataset = session_state.get('target_dataset', '')

        if step == 'schema_mapping':
            rerun_prompt = f"""Re-run Step 1: Schema Mapping with the following additional instructions from the user:

USER INSTRUCTIONS: {user_instructions}

Please regenerate the schema mapping between:
- Source: {staging_dataset}
- Target: {target_dataset}
- Mode: {mode}

Take into account the user's instructions when generating the mapping.

IMPORTANT: Provide results in JSON format with schema_mapping_result containing the full mapping data.
"""
        elif step == 'validation':
            last_result = pipeline_state.get('last_result', {})
            mapping_id = last_result.get('details', {}).get('mapping_id', '')
            rerun_prompt = f"""Re-run Step 2: Data Validation with the following additional instructions from the user:

USER INSTRUCTIONS: {user_instructions}

Please re-validate the data in staging dataset {staging_dataset} using the existing mapping.
mapping_id: {mapping_id}
Mode: {mode}

Take into account the user's instructions when performing validation.

IMPORTANT: Provide results in JSON format with validation_result_json containing the validation details.
"""
        elif step == 'etl':
            last_result = pipeline_state.get('last_result', {})
            mapping_id = last_result.get('details', {}).get('mapping_id', '')
            rerun_prompt = f"""Re-run Step 3: ETL SQL Generation with the following additional instructions from the user:

USER INSTRUCTIONS: {user_instructions}

Please regenerate the ETL SQL scripts for loading data from {staging_dataset} to {target_dataset}.
mapping_id: {mapping_id}

Take into account the user's instructions when generating the SQL.

IMPORTANT: Provide results in JSON format with the SQL scripts.
"""
        else:
            rerun_prompt = f"""Re-run the current step with the following additional instructions from the user:

USER INSTRUCTIONS: {user_instructions}

Please redo the current operation taking into account the user's feedback.
"""

        # Reset awaiting state
        pipeline_state['awaiting_continue'] = False

        # Run the re-run prompt in a separate thread using existing function
        thread = threading.Thread(target=run_agent_step_async, args=(rerun_prompt,))
        thread.start()

        return jsonify({
            'status': 'rerunning',
            'step': step,
            'message': f'Re-running {step} with user instructions'
        })

    except Exception as e:
        log_event(f"Error re-running step: {str(e)}", 'error')
        return jsonify({'error': str(e)}), 500


@app.route('/api/stream')
def stream():
    """Server-Sent Events stream for real-time updates."""
    def event_stream():
        while True:
            try:
                log_entry = event_queue.get(timeout=30)
                yield f"data: {log_entry}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"

    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/clear')
def clear_state():
    """Clear pipeline state and delete session datasets."""
    clear_session()
    log_event("Session cleared", 'info')
    return jsonify({'message': 'State cleared'})


if __name__ == '__main__':
    # Get port from environment variable (Cloud Run sets PORT)
    port = int(os.environ.get('PORT', 5001))

    print("\n GPT: Gen Prime Time Dashboard")
    print("=" * 60)
    print(f"  Dashboard URL: http://localhost:{port}")
    print(f"  BigQuery Available: {BIGQUERY_AVAILABLE}")
    if BIGQUERY_AVAILABLE:
        try:
            print(f"  Project ID: {get_project_id()}")
        except:
            print("  Project ID: Not configured")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")

    # In production (Cloud Run), debug should be False
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=port, threaded=True)
