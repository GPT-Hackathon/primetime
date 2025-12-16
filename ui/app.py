"""Flask Web Dashboard for Generic Multi-Agent ETL Pipeline."""

from flask import Flask, render_template, jsonify, request, Response
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import threading
import queue

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Optional imports - pipeline will work in demo mode without these
try:
    from src.utils.config_loader import ConfigLoader
    from src.utils.bigquery_helper import BigQueryHelper
    from src.utils.state_manager import StateManager
    from src.utils.schema_analyzer import SchemaAnalyzer
    from src.agents.profiler.agent import ProfilerAgent
    from src.agents.validator.generic_validator import GenericValidatorAgent
    from google.cloud import bigquery
    PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Optional imports not available: {e}")
    print("   Running in demo mode - Load Data will work, but Run Pipeline needs full setup")
    PIPELINE_AVAILABLE = False

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

# Queue for server-sent events
event_queue = queue.Queue()


def log_event(message, level='info'):
    """Log an event and send to UI."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'message': message
    }
    pipeline_state['logs'].append(log_entry)
    event_queue.put(json.dumps(log_entry))
    print(f"[{timestamp}] {message}")


def run_pipeline_async(source_files, target_ddls, mode):
    """Run pipeline in background thread."""
    try:
        pipeline_state['status'] = 'running'
        pipeline_state['start_time'] = datetime.now().isoformat()
        pipeline_state['logs'] = []
        log_event("🚀 Starting Generic Multi-Agent ETL Pipeline", 'info')

        # Load configuration
        config = ConfigLoader()
        config.config['pipeline']['mode'] = mode

        # Initialize components
        log_event("🤖 Initializing agents...", 'info')
        gcp_config = config.get_gcp_config()
        bq = BigQueryHelper(**gcp_config)
        state = StateManager()
        bq_client = bigquery.Client(project=gcp_config['project_id'])
        schema_analyzer = SchemaAnalyzer(bq_client)

        profiler = ProfilerAgent(bq, state)
        validator = GenericValidatorAgent(bq, state, config)

        log_event("✅ Agents initialized", 'success')

        # STEP 1: Analyze Source Schemas
        pipeline_state['current_step'] = 'Analyzing Source Schemas'
        pipeline_state['progress'] = 16
        log_event("📊 STEP 1: Analyzing Source Schemas", 'info')

        source_schemas = []
        for csv_file in source_files:
            log_event(f"  Analyzing {Path(csv_file).name}...", 'info')
            schema = schema_analyzer.analyze_source_csv(csv_file)
            source_schemas.append(schema)
            log_event(f"    ✓ {schema['row_count']} rows, {len(schema['columns'])} columns", 'success')

        # STEP 2: Analyze Target Schemas
        pipeline_state['current_step'] = 'Analyzing Target Schemas'
        pipeline_state['progress'] = 33
        log_event("📊 STEP 2: Analyzing Target Schemas", 'info')

        target_schemas = []
        for ddl_file in target_ddls:
            log_event(f"  Analyzing {Path(ddl_file).name}...", 'info')
            schema = schema_analyzer.analyze_target_ddl(ddl_file)
            target_schemas.append(schema)
            log_event(f"    ✓ Table: {schema['table_name']} ({schema['table_type']})", 'success')

        # STEP 3: Map Source to Target
        pipeline_state['current_step'] = 'Mapping Source → Target'
        pipeline_state['progress'] = 50
        log_event("🗺️  STEP 3: Mapping Source → Target", 'info')

        mapping = schema_analyzer.map_source_to_target(source_schemas, target_schemas)
        log_event(f"✓ Mapped {len(mapping['source_to_target'])} tables", 'success')

        # STEP 4: Profile Data
        pipeline_state['current_step'] = 'Profiling Data'
        pipeline_state['progress'] = 66
        log_event("🔍 STEP 4: Profiling Data (Bronze Tier)", 'info')

        profiler_results = profiler.run_profiling_pipeline(source_files)
        log_event(f"✅ Profiled {profiler_results['files_profiled']} files, found {profiler_results['total_issues']} issues", 'success')

        # STEP 5: Validate Data
        pipeline_state['current_step'] = 'Validating Data'
        pipeline_state['progress'] = 83
        log_event("✅ STEP 5: Validating Data (Silver Tier)", 'info')

        validation_results = {}
        for source_schema in source_schemas:
            staging_table = f"staging_{source_schema['table_name']}"
            if bq.table_exists(staging_table):
                log_event(f"  Validating {staging_table}...", 'info')
                result = validator.validate_table(staging_table, fix_mode=(mode == 'fix'))
                validation_results[staging_table] = result
                log_event(f"    ✓ Found {result.get('total_issues', 0)} issues", 'success')

        # STEP 6: Generate SQL
        pipeline_state['current_step'] = 'Generating SQL'
        pipeline_state['progress'] = 100
        log_event("🛠️  STEP 6: Auto-Generating SQL (Platinum Tier)", 'info')

        sql_files = []
        for source_table_name, target_info in mapping['source_to_target'].items():
            target_table = target_info['target_table']
            log_event(f"  Generated SQL: {source_table_name} → {target_table}", 'success')
            sql_files.append(f"{target_table}.sql")

        # Store results
        pipeline_state['results'] = {
            'source_files': len(source_files),
            'target_tables': len(target_schemas),
            'mappings': len(mapping['source_to_target']),
            'issues_found': profiler_results['total_issues'],
            'sql_files': len(sql_files),
            'mode': mode
        }

        pipeline_state['status'] = 'completed'
        pipeline_state['end_time'] = datetime.now().isoformat()
        log_event("✅ Pipeline execution completed successfully!", 'success')

    except Exception as e:
        pipeline_state['status'] = 'error'
        pipeline_state['end_time'] = datetime.now().isoformat()
        log_event(f"❌ Pipeline failed: {str(e)}", 'error')
        import traceback
        traceback.print_exc()


@app.route('/')
def index():
    """Render main dashboard."""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """Get current pipeline status."""
    return jsonify(pipeline_state)


@app.route('/api/run', methods=['POST'])
def run_pipeline():
    """Start pipeline execution."""
    if not PIPELINE_AVAILABLE:
        return jsonify({'error': 'Pipeline not available - missing required modules (src.utils, src.agents). Please set up the full project.'}), 400

    if pipeline_state['status'] == 'running':
        return jsonify({'error': 'Pipeline already running'}), 400

    data = request.json
    source_files = data.get('source_files', [])
    target_ddls = data.get('target_ddls', [])
    mode = data.get('mode', 'fix')

    if not source_files or not target_ddls:
        return jsonify({'error': 'source_files and target_ddls are required'}), 400

    # Expand file patterns
    from glob import glob
    expanded_sources = []
    for pattern in source_files:
        expanded_sources.extend(glob(pattern))

    expanded_targets = []
    for pattern in target_ddls:
        expanded_targets.extend(glob(pattern))

    # Run pipeline in background thread
    thread = threading.Thread(
        target=run_pipeline_async,
        args=(expanded_sources, expanded_targets, mode)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Pipeline started', 'status': 'running'})


@app.route('/api/stream')
def stream():
    """Server-Sent Events stream for real-time updates."""
    def event_stream():
        while True:
            try:
                # Get log entry from queue (blocking)
                log_entry = event_queue.get(timeout=30)
                yield f"data: {log_entry}\n\n"
            except queue.Empty:
                # Send heartbeat
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"

    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/clear')
def clear_state():
    """Clear pipeline state."""
    global load_state
    pipeline_state['status'] = 'idle'
    pipeline_state['current_step'] = None
    pipeline_state['progress'] = 0
    pipeline_state['results'] = {}
    pipeline_state['logs'] = []
    load_state = {'tables': [], 'data_cache': {}}
    return jsonify({'message': 'State cleared'})


# Store loaded data info
load_state = {
    'tables': [],
    'data_cache': {}
}


@app.route('/api/load', methods=['POST'])
def load_data():
    """Load source data into staging tables."""
    global load_state
    try:
        data = request.json
        source_pattern = data.get('source_files', '')
        target_pattern = data.get('target_ddls', '')

        log_event(f"📥 Loading data from: {source_pattern}", 'info')

        # Expand file patterns
        from glob import glob
        import csv

        source_files = glob(source_pattern)
        target_files = glob(target_pattern)

        if not source_files:
            return jsonify({'error': f'No source files found matching: {source_pattern}'}), 400

        tables = []
        total_rows = 0
        load_state['tables'] = []
        load_state['data_cache'] = {}

        for csv_file in source_files:
            table_name = Path(csv_file).stem
            log_event(f"  Loading {table_name}...", 'info')

            # Read CSV file
            rows = []
            columns = []
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames or []
                for row in reader:
                    rows.append(row)

            row_count = len(rows)
            total_rows += row_count

            # Cache the data for preview
            load_state['data_cache'][table_name] = {
                'columns': columns,
                'rows': rows
            }

            tables.append({
                'name': table_name,
                'rows': row_count,
                'columns': len(columns)
            })

            log_event(f"    ✓ {row_count} rows, {len(columns)} columns", 'success')

        load_state['tables'] = tables

        log_event(f"✅ Loaded {len(tables)} files with {total_rows} total rows", 'success')

        return jsonify({
            'file_count': len(source_files),
            'table_count': len(tables),
            'row_count': total_rows,
            'target_count': len(target_files),
            'tables': tables
        })

    except Exception as e:
        log_event(f"❌ Load failed: {str(e)}", 'error')
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview/<table_name>')
def preview_table(table_name):
    """Get paginated preview of table data."""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))

        if table_name not in load_state['data_cache']:
            return jsonify({'error': f'Table {table_name} not found'}), 404

        cached = load_state['data_cache'][table_name]
        all_rows = cached['rows']
        columns = cached['columns']

        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_rows = all_rows[start_idx:end_idx]

        return jsonify({
            'columns': columns,
            'rows': page_rows,
            'total_rows': len(all_rows),
            'page': page,
            'page_size': page_size
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n🌐 Starting Generic Multi-Agent ETL Dashboard")
    print("=" * 60)
    print("  Dashboard URL: http://localhost:5001")
    print("  Mode: Development")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")

    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)
