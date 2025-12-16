
import os
import json
from google.cloud import bigquery
from google.cloud import storage
from google.api_core.exceptions import NotFound

def get_project_id():
    """Gets the project ID from the environment."""
    # Use consistent env var names with fallback
    project_id = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID")
    if not project_id:
        raise ValueError("GCP_PROJECT_ID, GOOGLE_CLOUD_PROJECT, or PROJECT_ID environment variable not set.")
    return project_id

def find_schema_files_in_gcs(bucket_name: str, prefix: str = "") -> str:
    """
    Find all schema files (files with 'schema' in the name) in a GCS bucket/folder.
    
    Args:
        bucket_name: The GCS bucket name
        prefix: Optional prefix/folder path to search in
    
    Returns:
        JSON string with list of schema files found
    """
    try:
        project_id = get_project_id()
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        
        # List all blobs in the prefix
        blobs = list(bucket.list_blobs(prefix=prefix))
        
        # Find files with "schema" in the name (case-insensitive) and ending in .json
        schema_files = [
            {
                "path": blob.name,
                "name": os.path.basename(blob.name),
                "size_bytes": blob.size,
                "updated": blob.updated.isoformat() if blob.updated else None
            }
            for blob in blobs 
            if 'schema' in blob.name.lower() and blob.name.endswith('.json')
        ]
        
        return json.dumps({
            "status": "success",
            "bucket": bucket_name,
            "prefix": prefix or "/",
            "schema_files": schema_files,
            "count": len(schema_files)
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error finding schema files: {str(e)}"
        }, indent=2)


def load_csv_to_bigquery_from_gcs(
    dataset_name: str,
    bucket_name: str,
    file_path: str,
) -> str:
    """
    Loads a CSV file from GCS into a BigQuery table.

    - If the table exists, it appends the data.
    - If the table does not exist, it tries to create it.
    - When creating, it first looks for a 'schema.json' in the same GCS path.
    - If no schema file is found, it uses BigQuery's schema auto-detection.

    Args:
        dataset_name: The target BigQuery Dataset name.
        bucket_name: The GCS bucket name where the CSV file is located.
        file_path: The path to the CSV file within the GCS bucket.

    Returns:
        A message summarizing the result of the load operation.
    """
    try:
        project_id = get_project_id()
        bq_client = bigquery.Client(project=project_id)
        storage_client = storage.Client(project=project_id)
        print(f"Authenticated to BigQuery and GCS for project '{project_id}'.")
    except Exception as e:
        return f"Could not create BigQuery or GCS client. Check authentication. Error: {e}"

    table_name = os.path.splitext(os.path.basename(file_path))[0]
    table_id = f"{project_id}.{dataset_name}.{table_name}"
    gcs_uri = f"gs://{bucket_name}/{file_path}"

    print(f"Processing '{gcs_uri}' into BigQuery table '{table_id}'...")

    schema = None
    table_exists = True
    try:
        bq_client.get_table(table_id)
        print(f"Table '{table_id}' already exists. Appending data.")
        write_disposition = bigquery.WriteDisposition.WRITE_APPEND
    except NotFound:
        print(f"Table '{table_id}' not found. Attempting to create it.")
        table_exists = False
        write_disposition = bigquery.WriteDisposition.WRITE_EMPTY
        
        # Look for any schema file in the same GCS directory
        # Try multiple patterns: schema.json, *_schema.json, *schema*.json
        directory = os.path.dirname(file_path)
        try:
            bucket = storage_client.bucket(bucket_name)
            
            # List all files in the directory
            blobs = list(bucket.list_blobs(prefix=directory))
            
            # Find files with "schema" in the name (case-insensitive)
            schema_files = [
                blob for blob in blobs 
                if 'schema' in blob.name.lower() and blob.name.endswith('.json')
            ]
            
            if schema_files:
                # Use the first schema file found
                schema_blob = schema_files[0]
                schema_path = schema_blob.name
                print(f"Found schema file at 'gs://{bucket_name}/{schema_path}'.")
                
                schema_content = schema_blob.download_as_text()
                all_schemas = json.loads(schema_content)
                
                # Find the schema definition for the current table
                if table_name in all_schemas:
                    schema_definition = all_schemas[table_name]
                    schema = [bigquery.SchemaField.from_api_repr(field) for field in schema_definition]
                    print(f"Successfully parsed schema for table '{table_name}' from '{os.path.basename(schema_path)}'.")
                else:
                    print(f"Warning: Schema file '{os.path.basename(schema_path)}' found, but no entry for table '{table_name}'. "
                          "Falling back to auto-detection.")
            else:
                print(f"No schema file found in 'gs://{bucket_name}/{directory}/'. Using schema auto-detection.")
        except Exception as e:
            print(f"Warning: Error searching for or parsing schema file. Falling back to auto-detection. Error: {e}")

    # Configure the load job
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # Assumes a header row
        write_disposition=write_disposition,
    )

    if not table_exists:
        if schema:
            job_config.schema = schema
            job_config.autodetect = False
        else:
            job_config.autodetect = True

    try:
        load_job = bq_client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
        print(f"Starting BigQuery load job {load_job.job_id}...")

        load_job.result()  # Wait for the job to complete

        destination_table = bq_client.get_table(table_id)
        return (f"Successfully loaded {destination_table.num_rows} rows into "
                f"table '{table_id}'.")

    except Exception as e:
        return f"Failed to load data into BigQuery. Error: {e}"
