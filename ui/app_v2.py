"""Improved Flask Web Dashboard with folder selection and auto-trigger."""

from flask import Flask, render_template, jsonify, request, Response
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import threading
import queue
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.config_loader import ConfigLoader
from src.utils.bigquery_helper import BigQueryHelper
from src.utils.state_manager import StateManager
from src.utils.schema_analyzer import SchemaAnalyzer
from src.agents.profiler.agent import ProfilerAgent
from src.agents.validator.generic_validator import GenericValidatorAgent
from google.cloud import bigquery

app = Flask(__name__)

# Global state
pipeline_state = {
    'status': 'idle',
    'current_step': None,
    'progress': 0,
    'results': {},
    'logs': [],
    'error': None,
    'start_time': None,
    'end_time': None
}

event_queue = queue.Queue()


def log_event(message, level='info'):
    """Log event with proper error handling."""
    try:
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message
        }
        pipeline_state['logs'].append(log_entry)
        event_queue.put(json.dumps(log_entry))
        print(f"[{timestamp}] [{level.upper()}] {message}")
    except Exception as e:
        print(f"Error logging event: {e}")


def detect_file_type(file_path):
    """Detect file type from extension."""
    ext = Path(file_path).suffix.lower()

    # Data files
    if ext in ['.csv', '.tsv', '.txt']:
        return 'csv'
    elif ext in ['.json', '.jsonl']:
        return 'json'
    elif ext in ['.parquet', '.pq']:
        return 'parquet'
    elif ext in ['.xlsx', '.xls']:
        return 'excel'

    # Schema files
    elif ext in ['.sql', '.ddl']:
        return 'sql'
    elif ext in ['.yaml', '.yml']:
        return 'yaml'
    elif ext in ['.xml']:
        return 'xml'

    return 'unknown'


def get_files_from_folder(folder_path, file_types=['csv']):
    """Get all files of specified types from folder."""
    files = []
    folder = Path(folder_path)

    if not folder.exists():
        raise ValueError(f"Folder not found: {folder_path}")

    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")

    for file_type in file_types:
        if file_type == 'csv':
            files.extend(folder.glob("*.csv"))
            files.extend(folder.glob("*.tsv"))
            files.extend(folder.glob("*.txt"))
        elif file_type == 'json':
            files.extend(folder.glob("*.json"))
            files.extend(folder.glob("*.jsonl"))
        elif file_type == 'sql':
            files.extend(folder.glob("*.sql"))
            files.extend(folder.glob("*.ddl"))
        elif file_type == 'any':
            files.extend(folder.glob("*.*"))

    return [str(f) for f in files]


def run_pipeline_async(source_folder, target_folder, mode):
    """Run pipeline with comprehensive error handling."""
    try:
        log_event("🚀 Starting Generic Multi-Agent ETL Pipeline", 'info')
        pipeline_state['status'] = 'running'
        pipeline_state['error'] = None
        pipeline_state['start_time'] = datetime.now().isoformat()

        # Step 1: Validate folders
        log_event(f"📂 Validating folders...", 'info')

        if not source_folder or not target_folder:
            raise ValueError("Both source and target folders must be specified")

        source_path = Path(source_folder)
        target_path = Path(target_folder)

        if not source_path.exists():
            raise ValueError(f"Source folder not found: {source_folder}")

        if not target_path.exists():
            raise ValueError(f"Target folder not found: {target_folder}")

        log_event(f"✓ Source folder: {source_folder}", 'success')
        log_event(f"✓ Target folder: {target_folder}", 'success')

        # Step 2: Discover files
        log_event(f"🔍 Discovering files...", 'info')
        pipeline_state['current_step'] = 'Discovering Files'
        pipeline_state['progress'] = 10

        # Get source files (try CSV first, then any data file)
        source_files = get_files_from_folder(source_folder, ['csv'])
        if not source_files:
            log_event("No CSV files found, trying JSON...", 'warning')
            source_files = get_files_from_folder(source_folder, ['json'])
        if not source_files:
            log_event("No JSON files found, trying any data files...", 'warning')
            source_files = get_files_from_folder(source_folder, ['any'])

        # Get target files (try SQL first, then any schema file)
        target_files = get_files_from_folder(target_folder, ['sql'])
        if not target_files:
            log_event("No SQL files found in target folder", 'warning')
            target_files = []

        if not source_files:
            raise ValueError(f"No data files found in {source_folder}")

        log_event(f"✓ Found {len(source_files)} source files", 'success')
        for f in source_files:
            file_type = detect_file_type(f)
            log_event(f"  - {Path(f).name} ({file_type})", 'info')

        if target_files:
            log_event(f"✓ Found {len(target_files)} target schema files", 'success')
            for f in target_files:
                log_event(f"  - {Path(f).name}", 'info')
        else:
            log_event("⚠️  No target schema files - will infer from data", 'warning')

        # Step 3: Initialize agents
        log_event("🤖 Initializing agents...", 'info')
        pipeline_state['current_step'] = 'Initializing Agents'
        pipeline_state['progress'] = 20

        config = ConfigLoader()
        config.config['pipeline']['mode'] = mode
        gcp_config = config.get_gcp_config()

        bq = BigQueryHelper(**gcp_config)
        state = StateManager()
        bq_client = bigquery.Client(project=gcp_config['project_id'])
        schema_analyzer = SchemaAnalyzer(bq_client)

        profiler = ProfilerAgent(bq, state)
        validator = GenericValidatorAgent(bq, state, config)

        log_event("✅ Agents initialized successfully", 'success')

        # Step 4: Analyze schemas
        log_event("📊 Analyzing source schemas...", 'info')
        pipeline_state['current_step'] = 'Analyzing Source Schemas'
        pipeline_state['progress'] = 35

        source_schemas = []
        for i, csv_file in enumerate(source_files, 1):
            log_event(f"  [{i}/{len(source_files)}] Analyzing {Path(csv_file).name}...", 'info')
            try:
                schema = schema_analyzer.analyze_source_csv(csv_file)
                source_schemas.append(schema)
                log_event(f"    ✓ {schema['row_count']} rows, {len(schema['columns'])} columns", 'success')
            except Exception as e:
                log_event(f"    ✗ Error analyzing {Path(csv_file).name}: {str(e)}", 'error')

        if not source_schemas:
            raise ValueError("Failed to analyze any source files")

        # Step 5: Analyze target schemas
        pipeline_state['current_step'] = 'Analyzing Target Schemas'
        pipeline_state['progress'] = 50

        target_schemas = []
        if target_files:
            log_event("📊 Analyzing target schemas...", 'info')
            for i, ddl_file in enumerate(target_files, 1):
                log_event(f"  [{i}/{len(target_files)}] Analyzing {Path(ddl_file).name}...", 'info')
                try:
                    schema = schema_analyzer.analyze_target_ddl(ddl_file)
                    target_schemas.append(schema)
                    log_event(f"    ✓ Table: {schema['table_name']} ({schema['table_type']})", 'success')
                except Exception as e:
                    log_event(f"    ✗ Error analyzing {Path(ddl_file).name}: {str(e)}", 'error')

        # Step 6: Map schemas
        pipeline_state['current_step'] = 'Mapping Schemas'
        pipeline_state['progress'] = 65

        if target_schemas:
            log_event("🗺️  Mapping source → target...", 'info')
            mapping = schema_analyzer.map_source_to_target(source_schemas, target_schemas)
            log_event(f"✓ Mapped {len(mapping['source_to_target'])} tables", 'success')
        else:
            log_event("⚠️  No target schemas - skipping mapping", 'warning')
            mapping = {'source_to_target': {}, 'unmapped_sources': [], 'unmapped_targets': []}

        # Step 7: Profile data
        pipeline_state['current_step'] = 'Profiling Data'
        pipeline_state['progress'] = 80

        log_event("🔍 Profiling data quality...", 'info')
        profiler_results = profiler.run_profiling_pipeline(source_files)
        log_event(f"✅ Profiled {profiler_results['files_profiled']} files", 'success')
        log_event(f"  Found {profiler_results['total_issues']} data quality issues", 'info')

        # Step 8: Validate data
        pipeline_state['current_step'] = 'Validating Data'
        pipeline_state['progress'] = 90

        log_event("✅ Validating data...", 'info')
        validation_results = {}

        for source_schema in source_schemas:
            staging_table = f"staging_{source_schema['table_name']}"
            if bq.table_exists(staging_table):
                log_event(f"  Validating {staging_table}...", 'info')
                try:
                    result = validator.validate_table(staging_table, fix_mode=(mode == 'fix'))
                    validation_results[staging_table] = result
                    log_event(f"    ✓ Found {result.get('total_issues', 0)} issues", 'success')
                except Exception as e:
                    log_event(f"    ✗ Validation error: {str(e)}", 'error')

        # Step 9: Complete
        pipeline_state['current_step'] = 'Complete'
        pipeline_state['progress'] = 100

        pipeline_state['results'] = {
            'source_files': len(source_files),
            'target_schemas': len(target_schemas),
            'mappings': len(mapping['source_to_target']),
            'issues_found': profiler_results['total_issues'],
            'mode': mode
        }

        pipeline_state['status'] = 'completed'
        pipeline_state['end_time'] = datetime.now().isoformat()

        duration = (datetime.fromisoformat(pipeline_state['end_time']) -
                   datetime.fromisoformat(pipeline_state['start_time'])).total_seconds()

        log_event(f"✅ Pipeline completed successfully in {duration:.2f} seconds!", 'success')

    except Exception as e:
        pipeline_state['status'] = 'error'
        pipeline_state['error'] = str(e)
        pipeline_state['end_time'] = datetime.now().isoformat()
        log_event(f"❌ Pipeline failed: {str(e)}", 'error')

        import traceback
        error_details = traceback.format_exc()
        log_event(f"Error details:\n{error_details}", 'error')


@app.route('/')
def index():
    return render_template('dashboard_v2.html')


@app.route('/api/status')
def get_status():
    return jsonify(pipeline_state)


@app.route('/api/folders')
def list_folders():
    """List available folders."""
    try:
        cwd = Path.cwd()
        folders = [str(f.relative_to(cwd)) for f in cwd.rglob('*') if f.is_dir() and not f.name.startswith('.')]
        folders = sorted(folders[:50])  # Limit to 50
        return jsonify({'folders': folders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/run', methods=['POST'])
def run_pipeline():
    """Start pipeline."""
    if pipeline_state['status'] == 'running':
        return jsonify({'error': 'Pipeline already running'}), 400

    data = request.json
    source_folder = data.get('source_folder')
    target_folder = data.get('target_folder')
    mode = data.get('mode', 'fix')

    if not source_folder or not target_folder:
        return jsonify({'error': 'source_folder and target_folder required'}), 400

    # Reset state
    pipeline_state['logs'] = []
    pipeline_state['results'] = {}
    pipeline_state['error'] = None

    # Run in background
    thread = threading.Thread(
        target=run_pipeline_async,
        args=(source_folder, target_folder, mode)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Pipeline started', 'status': 'running'})


@app.route('/api/stream')
def stream():
    """SSE stream."""
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
    pipeline_state['status'] = 'idle'
    pipeline_state['current_step'] = None
    pipeline_state['progress'] = 0
    pipeline_state['results'] = {}
    pipeline_state['logs'] = []
    pipeline_state['error'] = None
    return jsonify({'message': 'State cleared'})


if __name__ == '__main__':
    print("\n🌐 Starting Improved Generic Multi-Agent ETL Dashboard")
    print("=" * 60)
    print("  Dashboard URL: http://localhost:5001")
    print("  Features:")
    print("    ✓ Folder selection (not file patterns)")
    print("    ✓ Supports ANY file type")
    print("    ✓ Better error handling")
    print("    ✓ Real-time progress updates")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")

    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)
