import os
import json
import base64
from io import BytesIO
from google.cloud import bigquery
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

# Import visualization libraries
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import pandas as pd
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False


def get_dataset_schema(dataset_name: str, project_id: str = None) -> str:
    """
    Get the schema (table names and column definitions) for a BigQuery dataset.

    This is useful for understanding what tables and columns are available
    before writing SQL queries.

    Args:
        dataset_name: The name of the BigQuery dataset to inspect
        project_id: Optional project ID (uses env var if not provided)

    Returns:
        A JSON string containing the dataset schema information
    """
    if not project_id:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        return json.dumps({
            "status": "error",
            "message": "PROJECT_ID not found. Set GOOGLE_CLOUD_PROJECT env var."
        })

    try:
        client = bigquery.Client(project=project_id)
        dataset_ref = f"{project_id}.{dataset_name}"

        # List all tables in the dataset
        tables = list(client.list_tables(dataset_ref))

        if not tables:
            return json.dumps({
                "status": "success",
                "dataset": dataset_name,
                "project": project_id,
                "tables": [],
                "message": f"Dataset '{dataset_name}' exists but has no tables."
            })

        schema_info = {
            "status": "success",
            "dataset": dataset_name,
            "project": project_id,
            "tables": []
        }

        # Get schema for each table
        for table_item in tables:
            table = client.get_table(table_item.reference)

            columns = []
            for field in table.schema:
                columns.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description or ""
                })

            schema_info["tables"].append({
                "table_name": table.table_id,
                "num_rows": table.num_rows,
                "num_columns": len(columns),
                "columns": columns
            })

        return json.dumps(schema_info, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error getting dataset schema: {str(e)}"
        })


def execute_sql_query(query: str, dataset_name: str = None, project_id: str = None) -> str:
    """
    Execute a SQL query directly in BigQuery and return results.

    Use this to run SQL queries generated from natural language questions.
    The query can reference tables in the specified dataset.

    Args:
        query: The SQL query to execute
        dataset_name: Optional default dataset name for unqualified table names
        project_id: Optional project ID (uses env var if not provided)

    Returns:
        A string containing the query results or error message
    """
    if not project_id:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        return json.dumps({
            "status": "error",
            "message": "PROJECT_ID not found. Set GOOGLE_CLOUD_PROJECT env var."
        })

    try:
        client = bigquery.Client(project=project_id)

        # Set default dataset if provided
        job_config = bigquery.QueryJobConfig()
        if dataset_name:
            job_config.default_dataset = f"{project_id}.{dataset_name}"

        print(f"Executing query: {query}")

        # Execute the query
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        # Format results
        rows = []
        for row in results:
            row_dict = dict(row.items())
            rows.append(row_dict)

        if not rows:
            return json.dumps({
                "status": "success",
                "message": "Query executed successfully. No rows returned.",
                "query": query,
                "row_count": 0,
                "results": []
            }, indent=2)

        return json.dumps({
            "status": "success",
            "message": f"Query executed successfully. Returned {len(rows)} rows.",
            "query": query,
            "row_count": len(rows),
            "results": rows[:100]  # Limit to first 100 rows for display
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error executing query: {str(e)}",
            "query": query
        })


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


def generate_graph(query: str, dataset_name: str, graph_type: str = "bar",
                   x_column: str = None, y_column: str = None,
                   title: str = None, save_to_gcs: bool = False,
                   bucket_name: str = None, project_id: str = None) -> str:
    """
    Execute a query and generate a graph/chart from the results.

    Supports bar charts, line charts, pie charts, and scatter plots.
    Can save to GCS or return as base64-encoded image.

    Args:
        query: SQL query to execute
        dataset_name: BigQuery dataset name
        graph_type: Type of graph - "bar", "line", "pie", "scatter", "histogram"
        x_column: Column name for X-axis (required for bar, line, scatter)
        y_column: Column name for Y-axis (required for bar, line, scatter)
        title: Optional title for the graph
        save_to_gcs: If True, save to GCS bucket instead of returning base64
        bucket_name: GCS bucket name (required if save_to_gcs=True)
        project_id: Optional project ID

    Returns:
        JSON with graph data (base64 image or GCS path) and metadata
    """
    if not VISUALIZATION_AVAILABLE:
        return json.dumps({
            "status": "error",
            "message": "Visualization libraries not available. Install: pip install matplotlib pandas"
        })

    if not project_id:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        return json.dumps({
            "status": "error",
            "message": "PROJECT_ID not found. Set GOOGLE_CLOUD_PROJECT env var."
        })

    try:
        # Execute query
        client = bigquery.Client(project=project_id)
        job_config = bigquery.QueryJobConfig()
        if dataset_name:
            job_config.default_dataset = f"{project_id}.{dataset_name}"

        print(f"Executing query for graph: {query}")

        # Add LIMIT if not present for performance
        query_upper = query.upper()
        if 'LIMIT' not in query_upper:
            query = f"{query} LIMIT 500"
            print(f"Added LIMIT 500 for performance")

        query_job = client.query(query, job_config=job_config)

        print("Waiting for query to complete...")
        results = query_job.result()

        print("Converting results to DataFrame...")
        df = results.to_dataframe()

        print(f"Got {len(df)} rows for chart")

        if df.empty:
            return json.dumps({
                "status": "error",
                "message": "Query returned no data to plot"
            })

        # Auto-detect columns if not specified
        if not x_column and len(df.columns) > 0:
            x_column = df.columns[0]
        if not y_column and len(df.columns) > 1:
            y_column = df.columns[1]

        # Create figure
        plt.figure(figsize=(10, 6))

        # Generate appropriate graph type
        if graph_type == "bar":
            if x_column and y_column:
                plt.bar(df[x_column].astype(str), df[y_column])
                plt.xlabel(x_column)
                plt.ylabel(y_column)
                plt.xticks(rotation=45, ha='right')

        elif graph_type == "line":
            if x_column and y_column:
                plt.plot(df[x_column], df[y_column], marker='o')
                plt.xlabel(x_column)
                plt.ylabel(y_column)
                plt.xticks(rotation=45, ha='right')

        elif graph_type == "pie":
            # For pie chart, use first column as labels, second as values
            if len(df.columns) >= 2:
                plt.pie(df[y_column], labels=df[x_column].astype(str), autopct='%1.1f%%')
            else:
                plt.pie(df[df.columns[0]], autopct='%1.1f%%')

        elif graph_type == "scatter":
            if x_column and y_column:
                plt.scatter(df[x_column], df[y_column])
                plt.xlabel(x_column)
                plt.ylabel(y_column)

        elif graph_type == "histogram":
            plt.hist(df[y_column] if y_column else df[df.columns[0]], bins=20)
            plt.xlabel(y_column if y_column else df.columns[0])
            plt.ylabel("Frequency")

        else:
            return json.dumps({
                "status": "error",
                "message": f"Unsupported graph type: {graph_type}. Use: bar, line, pie, scatter, histogram"
            })

        # Set title
        if title:
            plt.title(title)
        else:
            plt.title(f"{graph_type.capitalize()} Chart")

        plt.tight_layout()

        # Save or return graph
        if save_to_gcs and bucket_name:
            # Save to GCS
            filename = f"graphs/{graph_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"

            # Save to buffer first
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)

            # Upload to GCS
            storage_client = storage.Client(project=project_id)
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(filename)
            blob.upload_from_file(buffer, content_type='image/png')

            # Generate a signed URL (valid for 1 hour)
            from datetime import timedelta
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=1),
                method="GET"
            )

            gcs_path = f"gs://{bucket_name}/{filename}"
            plt.close()

            return json.dumps({
                "status": "success",
                "message": "Graph generated and saved to GCS with signed URL",
                "graph_type": graph_type,
                "gcs_path": gcs_path,
                "signed_url": signed_url,
                "url_expires_in": "1 hour",
                "rows_plotted": len(df),
                "columns_used": {
                    "x": x_column,
                    "y": y_column
                }
            }, indent=2)

        else:
            # Return as base64
            print("Generating chart image...")
            buffer = BytesIO()
            # Use lower DPI (72) for faster generation - still looks good on screen
            plt.savefig(buffer, format='png', dpi=72, bbox_inches='tight')
            buffer.seek(0)
            print("Encoding image to base64...")
            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close()
            print("Chart generation complete!")

            return json.dumps({
                "status": "success",
                "message": "Graph generated successfully",
                "graph_type": graph_type,
                "image_base64": img_base64,
                "rows_plotted": len(df),
                "columns_used": {
                    "x": x_column,
                    "y": y_column
                },
                "note": "Use the image_base64 field to display the graph. Prefix with: data:image/png;base64,"
            }, indent=2)

    except Exception as e:
        plt.close()
        return json.dumps({
            "status": "error",
            "message": f"Error generating graph: {str(e)}",
            "query": query
        })
