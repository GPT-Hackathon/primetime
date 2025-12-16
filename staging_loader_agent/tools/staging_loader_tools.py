
import os
import json
from google.cloud import bigquery
from google.cloud import storage
from google.api_core.exceptions import NotFound

def get_project_id():
    """Gets the project ID from the environment."""
    project_id = os.environ.get("PROJECT_ID")
    if not project_id:
        raise ValueError("PROJECT_ID environment variable not set.")
    return project_id

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
        
        # Look for schema.json in the same GCS directory
        schema_path = os.path.join(os.path.dirname(file_path), "schema.json")
        try:
            bucket = storage_client.bucket(bucket_name)
            schema_blob = bucket.blob(schema_path)
            if schema_blob.exists():
                print(f"Found schema file at 'gs://{bucket_name}/{schema_path}'.")
                schema_content = schema_blob.download_as_text()
                all_schemas = json.loads(schema_content)
                
                # Find the schema definition for the current table
                if table_name in all_schemas:
                    schema_definition = all_schemas[table_name]
                    schema = [bigquery.SchemaField.from_api_repr(field) for field in schema_definition]
                    print(f"Successfully parsed schema for table '{table_name}'.")
                else:
                    print(f"Warning: Schema file found, but no entry for table '{table_name}'. "
                          "Falling back to auto-detection.")
            else:
                print("No 'schema.json' found. Using schema auto-detection.")
        except Exception as e:
            print(f"Warning: Error reading or parsing schema file. Falling back to auto-detection. Error: {e}")

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
