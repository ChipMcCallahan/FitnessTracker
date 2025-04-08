import functools
import logging
from datetime import date
from google.cloud import bigquery
from google.api_core.exceptions import NotFound

# Set up a logger
logger = logging.getLogger(__name__)

PROJECT_ID = "linux-instance-228201"
DATASET_ID = "fitness"
WORKOUT_TYPES_TABLE = "workout_types"
LEDGER_TABLE = "ledger"

# Fully qualified table IDs
WORKOUT_TYPES_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{WORKOUT_TYPES_TABLE}"
LEDGER_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{LEDGER_TABLE}"

@functools.lru_cache(maxsize=1)
def get_bq_client() -> bigquery.Client:
    """Return a cached BigQuery client (assumes application default credentials)."""
    return bigquery.Client(project=PROJECT_ID)

def ensure_dataset_and_tables() -> None:
    """
    Checks if the dataset 'fitness' exists. If not, creates it.
    Then checks for the workout_types and ledger tables, creating if needed.
    """
    client = get_bq_client()

    # Ensure Dataset Exists
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset '{DATASET_ID}' already exists.")
    except NotFound:
        dataset_ref.location = "US"  # Set your preferred location
        dataset = client.create_dataset(dataset_ref)
        logger.info(f"Created dataset '{dataset.dataset_id}'.")

    # Ensure workout_types Table Exists
    schema_workout_types = [
        bigquery.SchemaField("workout_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("unit", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("is_int", "BOOL", mode="REQUIRED"),
    ]
    create_table_if_not_exists(WORKOUT_TYPES_TABLE_ID, schema_workout_types)

    # Ensure ledger Table Exists
    schema_ledger = [
        bigquery.SchemaField("workout_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("amount", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("unit", "STRING", mode="REQUIRED"),
    ]
    create_table_if_not_exists(LEDGER_TABLE_ID, schema_ledger)


def create_table_if_not_exists(table_id: str, schema: list) -> None:
    """
    Checks if a table exists; if not, creates it with the given schema.
    """
    client = get_bq_client()
    try:
        client.get_table(table_id)
        logger.info(f"Table '{table_id}' already exists.")
    except NotFound:
        table = bigquery.Table(table_id, schema=schema)
        client.create_table(table)
        logger.info(f"Created table '{table_id}'.")

def create_workout_type(workout_type: str, unit: str, is_int: bool) -> None:
    """
    Inserts a new row into workout_types table.
    """
    client = get_bq_client()
    rows_to_insert = [
        {
            "workout_type": workout_type,
            "unit": unit,
            "is_int": is_int
        }
    ]
    errors = client.insert_rows_json(WORKOUT_TYPES_TABLE_ID, rows_to_insert)
    if errors:
        raise Exception(f"Error inserting workout type: {errors}")
    logger.info(f"Created workout type '{workout_type}' with unit '{unit}', is_int={is_int}.")

def read_workout_types() -> list:
    """
    Returns a list of dicts with workout_type, unit, is_int.
    """
    client = get_bq_client()
    query = f"""
        SELECT workout_type, unit, is_int
        FROM `{WORKOUT_TYPES_TABLE_ID}`
        ORDER BY workout_type
    """
    job = client.query(query)
    results = [dict(row) for row in job.result()]
    logger.info(f"Read {len(results)} workout types.")
    return results

def update_workout_type(old_workout_type: str, new_workout_type: str, new_unit: str, new_is_int: bool) -> None:
    """
    Updates an existing workout_type row.
    """
    client = get_bq_client()
    query = f"""
        UPDATE `{WORKOUT_TYPES_TABLE_ID}`
        SET workout_type = @new_workout_type,
            unit = @new_unit,
            is_int = @new_is_int
        WHERE workout_type = @old_workout_type
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("new_workout_type", "STRING", new_workout_type),
            bigquery.ScalarQueryParameter("new_unit", "STRING", new_unit),
            bigquery.ScalarQueryParameter("new_is_int", "BOOL", new_is_int),
            bigquery.ScalarQueryParameter("old_workout_type", "STRING", old_workout_type),
        ]
    )
    client.query(query, job_config=job_config).result()
    logger.info(f"Updated workout type '{old_workout_type}' to '{new_workout_type}' with unit '{new_unit}', is_int={new_is_int}.")

def delete_workout_type(workout_type: str) -> None:
    """
    Deletes an existing workout_type row.
    """
    client = get_bq_client()
    query = f"""
        DELETE FROM `{WORKOUT_TYPES_TABLE_ID}`
        WHERE workout_type = @workout_type
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("workout_type", "STRING", workout_type)
        ]
    )
    client.query(query, job_config=job_config).result()
    logger.info(f"Deleted workout type '{workout_type}'.")

def log_workout(workout_type: str, date_value: date, amount: float, unit: str) -> None:
    """
    Logs a new workout in the ledger table.
    """
    client = get_bq_client()
    rows_to_insert = [
        {
            "workout_type": workout_type,
            "date": str(date_value),  # BigQuery DATE in YYYY-MM-DD format
            "amount": amount,
            "unit": unit
        }
    ]
    errors = client.insert_rows_json(LEDGER_TABLE_ID, rows_to_insert)
    if errors:
        raise Exception(f"Error inserting ledger entry: {errors}")
    logger.info(f"Logged workout: {workout_type}, {amount} {unit} on {date_value}.")

def read_workouts(filter_type: str = None) -> list:
    """
    Reads workouts from the ledger, optionally filtered by workout_type.
    Ordered by most recent date first.
    """
    client = get_bq_client()
    base_query = f"""
        SELECT
            workout_type,
            date,
            amount,
            unit
        FROM `{LEDGER_TABLE_ID}`
    """
    if filter_type:
        base_query += " WHERE workout_type = @filter_type"
    base_query += " ORDER BY date DESC"

    if filter_type:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("filter_type", "STRING", filter_type)]
        )
        job = client.query(base_query, job_config=job_config)
    else:
        job = client.query(base_query)

    results = [dict(row) for row in job.result()]
    logger.info(
        f"Read {len(results)} workouts from ledger."
        + (f" (Filtered by '{filter_type}')" if filter_type else "")
    )
    return results
