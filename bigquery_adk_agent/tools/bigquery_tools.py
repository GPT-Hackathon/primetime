import os
from google.cloud import bigquery
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

def execute_sql_from_gcs(bucket_name: str, blob_name: str, dataset_name: str, hardcoded_dataset_to_replace: str = None) -> str:
    """
    Executes a SQL query from a file in GCS on a specified BigQuery dataset.

    Args:
        bucket_name: The name of the GCS bucket.
        blob_name: The full path to the SQL file in the GCS bucket.
        dataset_name: The name of the BigQuery dataset to execute the query against.
        hardcoded_dataset_to_replace: An optional hardcoded dataset name in the SQL file to be replaced with the `dataset_name`.

    Returns:
        A string containing the query results.
    """
    # 1. Read PROJECT_ID from environment
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        # As a fallback, let the google-cloud client try to infer the project
        try:
            client = bigquery.Client()
            if getattr(client, "project", None):
                project_id = client.project
        except Exception:
            # If the client can't be initialized (missing credentials/packages), ignore and raise below
            pass

    if not project_id:
        raise ValueError(
            "PROJECT_ID environment variable not set. "
            "Set `GOOGLE_CLOUD_PROJECT`, or run `gcloud config set project YOUR_PROJECT_ID" \
            "or configure Application Default Credentials."
        )

    # 2. Initialize clients
    bigquery_client = bigquery.Client(project=project_id)
    storage_client = storage.Client(project=project_id)

    # 3. Read the SQL file from GCS
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    query_sql = blob.download_as_text()

    # 4. Replace dataset and placeholders
    if hardcoded_dataset_to_replace:
        query_sql = query_sql.replace(f"{hardcoded_dataset_to_replace}.", f"{dataset_name}.")

    query_sql = query_sql.replace("your-gcp-project-id", project_id)
    query_sql = query_sql.replace("your_dataset_name", dataset_name)

    print(f"Executing query: {query_sql}")

    # 5. Execute the query
    try:
        query_job = bigquery_client.query(query_sql)
        results = query_job.result()
        rows = [str(row) for row in results]
        if not rows:
            return "Query executed successfully and returned no rows."
        return "\n".join(rows)
    except Exception as e:
        return f"Error executing query: {e}"