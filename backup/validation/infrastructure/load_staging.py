#!/usr/bin/env python3
"""
Simple CSV to BigQuery Loader
Dumps raw CSV files into BigQuery tables with no schema enforcement.
"""

import os
import glob
from google.cloud import bigquery


def load_csv_to_bigquery(csv_file_path, project_id, dataset_id, table_name):
    """
    Load a single CSV file into BigQuery.
    Reads column names from CSV header, stores all data as STRING.

    Args:
        csv_file_path: Path to CSV file
        project_id: GCP project ID
        dataset_id: BigQuery dataset name
        table_name: Target table name
    """
    client = bigquery.Client(project=project_id)

    table_id = f"{project_id}.{dataset_id}.{table_name}"

    # Read column names from CSV header
    with open(csv_file_path, 'r') as f:
        header_line = f.readline().strip()
        column_names = [name.strip() for name in header_line.split(',')]

    # Create schema with column names (all STRING - raw dump, no type conversion)
    schema = [bigquery.SchemaField(name, "STRING", mode="NULLABLE") for name in column_names]

    # Load config - use header column names but keep everything as STRING
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )

    print(f"Loading {csv_file_path} → {table_id}")

    with open(csv_file_path, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)

    job.result()  # Wait for completion

    table = client.get_table(table_id)
    print(f"  ✓ Loaded {table.num_rows} rows ({len(column_names)} columns)\n")

    return table.num_rows


def load_directory(source_dir, project_id, dataset_id, file_pattern="*.csv"):
    """
    Load all CSV files from a directory into BigQuery.
    Table names are derived from filenames (without .csv extension).

    Args:
        source_dir: Directory containing CSV files
        project_id: GCP project ID
        dataset_id: BigQuery dataset name
        file_pattern: File pattern to match (default: *.csv)
    """
    print(f"Loading CSV files from: {source_dir}")
    print(f"Target: {project_id}.{dataset_id}")
    print("=" * 60 + "\n")

    csv_files = glob.glob(os.path.join(source_dir, file_pattern))

    if not csv_files:
        print(f"No CSV files found in {source_dir}")
        return

    total_rows = 0
    loaded_count = 0

    for csv_file in sorted(csv_files):
        filename = os.path.basename(csv_file)
        table_name = filename.replace('.csv', '').replace('source_', '')

        try:
            rows = load_csv_to_bigquery(csv_file, project_id, dataset_id, table_name)
            total_rows += rows
            loaded_count += 1
        except Exception as e:
            print(f"  ✗ Error: {e}\n")

    print("=" * 60)
    print(f"Summary: Loaded {loaded_count}/{len(csv_files)} files ({total_rows:,} total rows)")
    print("=" * 60)


if __name__ == "__main__":
    # Configuration
    PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ccibt-hack25ww7-750")
    DATASET_ID = os.getenv("BQ_DATASET_ID", "test_staging_dataset")

    # Path to CSV files
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    DATA_DIR = os.path.join(BASE_DIR, "dataSets/Sample-DataSet-WorldBankData/SourceSchemaData")

    # Load all CSV files
    load_directory(DATA_DIR, PROJECT_ID, DATASET_ID)
