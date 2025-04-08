# tests/test_workout_dao.py
import unittest
from unittest.mock import patch, MagicMock
from datetime import date
from typing import List, Dict, Any

import pandas as pd
from google.api_core.exceptions import NotFound

# Import your DAO functions
from dao.workout_dao import (
    ensure_dataset_and_tables,
    create_workout_type,
    read_workout_types,
    update_workout_type,
    delete_workout_type,
    log_workout,
    read_workouts,
    WORKOUT_TYPES_TABLE_ID,
    LEDGER_TABLE_ID, create_table_if_not_exists
)


class TestWorkoutDAO(unittest.TestCase):
    @patch("dao.workout_dao.get_bq_client")
    def test_ensure_dataset_and_tables_dataset_exists(self, mock_get_client: MagicMock) -> None:
        """
        Test ensure_dataset_and_tables when the dataset already exists.
        """
        # Mock get_dataset to not raise an exception => dataset exists
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # We expect 'get_table' calls to check the tables
        # We'll mock them so they appear to already exist
        mock_client.get_table.side_effect = [MagicMock(), MagicMock()]

        ensure_dataset_and_tables()

        # Verify calls
        mock_client.get_dataset.assert_called_once()
        self.assertEqual(mock_client.get_table.call_count, 2)
        mock_client.create_dataset.assert_not_called()  # dataset already exists, so no creation
        mock_client.create_table.assert_not_called()  # tables already exist

    @patch("dao.workout_dao.get_bq_client")
    def test_ensure_dataset_and_tables_dataset_not_exists(self, mock_get_client: MagicMock) -> None:
        """
        Test ensure_dataset_and_tables when the dataset does NOT exist yet.
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_dataset.side_effect = NotFound("Dataset not found")

        # Also pretend the tables do not exist
        mock_client.get_table.side_effect = NotFound("Table not found")

        ensure_dataset_and_tables()

        # check that create_dataset was called
        mock_client.create_dataset.assert_called_once()
        # for the two tables
        self.assertEqual(mock_client.create_table.call_count, 2)

    @patch("dao.workout_dao.get_bq_client")
    def test_create_table_if_not_exists_already_exists(self, mock_get_client: MagicMock) -> None:
        """
        Test that _create_table_if_not_exists doesn't create the table
        if it already exists.
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        # calling the internal helper directly:
        create_table_if_not_exists(WORKOUT_TYPES_TABLE_ID, [])
        mock_client.create_table.assert_not_called()

    @patch("dao.workout_dao.get_bq_client")
    def test_create_table_if_not_exists_not_found(self, mock_get_client: MagicMock) -> None:
        """
        Test that create_table_if_not_exists creates the table
        if it does not exist.
        """
        from google.api_core.exceptions import NotFound

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Simulate "Table not found" so that your function tries to create the table.
        mock_client.get_table.side_effect = NotFound("Table not found")

        create_table_if_not_exists(WORKOUT_TYPES_TABLE_ID, [])
        mock_client.create_table.assert_called_once()

    @patch("dao.workout_dao.get_bq_client")
    def test_create_workout_type(self, mock_get_client: MagicMock) -> None:
        """
        Test creating a workout type.
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.insert_rows_json.return_value = []

        create_workout_type("pushups", "reps", True)
        mock_client.insert_rows_json.assert_called_once()
        # Extract the call args
        args, kwargs = mock_client.insert_rows_json.call_args
        self.assertEqual(args[0], WORKOUT_TYPES_TABLE_ID)
        self.assertEqual(args[1][0]["workout_type"], "pushups")
        self.assertEqual(args[1][0]["unit"], "reps")
        self.assertTrue(args[1][0]["is_int"])

    @patch("dao.workout_dao.get_bq_client")
    def test_create_workout_type_error(self, mock_get_client: MagicMock) -> None:
        """
        Test create_workout_type when there's an insertion error.
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.insert_rows_json.return_value = ["Some error"]
        with self.assertRaises(Exception) as context:
            create_workout_type("pushups", "reps", True)
        self.assertIn("Error inserting workout type", str(context.exception))

    @patch("dao.workout_dao.get_bq_client")
    def test_read_workout_types(self, mock_get_client: MagicMock) -> None:
        """
        Test reading workout types.
        """
        # mock_client.query().result() should return an iterable of rows
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = [
            {"workout_type": "pushups", "unit": "reps", "is_int": True},
            {"workout_type": "running", "unit": "miles", "is_int": False},
        ]
        mock_client.query.return_value = mock_query_job

        result: List[Dict[str, Any]] = read_workout_types()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["workout_type"], "pushups")
        self.assertTrue(result[0]["is_int"])
        self.assertEqual(result[1]["workout_type"], "running")
        self.assertFalse(result[1]["is_int"])

    @patch("dao.workout_dao.get_bq_client")
    def test_update_workout_type(self, mock_get_client: MagicMock) -> None:
        """
        Test updating a workout type.
        """
        # We'll just check that client.query() was called with the correct query
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        update_workout_type("pushups", "situps", "reps", True)
        mock_client.query.assert_called_once()

        called_query = mock_client.query.call_args[0][0]
        self.assertIn("UPDATE", called_query)
        self.assertIn("workout_type = @old_workout_type", called_query)

    @patch("dao.workout_dao.get_bq_client")
    def test_delete_workout_type(self, mock_get_client: MagicMock) -> None:
        """
        Test deleting a workout type.
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        delete_workout_type("pushups")
        mock_client.query.assert_called_once()
        called_query = mock_client.query.call_args[0][0]
        self.assertIn("DELETE FROM", called_query)

    @patch("dao.workout_dao.get_bq_client")
    def test_log_workout(self, mock_get_client: MagicMock) -> None:
        """
        Test logging a workout to the ledger.
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.insert_rows_json.return_value = []
        log_workout("pushups", date(2025, 4, 7), 25.0, "reps")

        mock_client.insert_rows_json.assert_called_once()
        args, _ = mock_client.insert_rows_json.call_args
        self.assertEqual(args[0], LEDGER_TABLE_ID)
        self.assertEqual(args[1][0]["workout_type"], "pushups")
        self.assertEqual(args[1][0]["date"], "2025-04-07")
        self.assertEqual(args[1][0]["amount"], 25.0)
        self.assertEqual(args[1][0]["unit"], "reps")

    @patch("dao.workout_dao.get_bq_client")
    def test_log_workout_error(self, mock_get_client: MagicMock) -> None:
        """
        Test log_workout if there's an insertion error.
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.insert_rows_json.return_value = ["Insert error"]
        with self.assertRaises(Exception) as context:
            log_workout("pushups", date.today(), 25.0, "reps")
        self.assertIn("Error inserting ledger entry", str(context.exception))

    @patch("dao.workout_dao.get_bq_client")
    def test_read_workouts_no_filter(self, mock_get_client: MagicMock) -> None:
        """Test reading workouts with no filter, returning a DataFrame."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create a mock query job object and specify the .to_dataframe() return value
        mock_query_job = MagicMock()
        mock_df = pd.DataFrame([
            {"workout_type": "pushups", "date": date(2025, 4, 7), "amount": 25.0, "unit": "reps"},
            {"workout_type": "running", "date": date(2025, 4, 6), "amount": 5.0, "unit": "miles"},
        ])
        # The .query(...) call will return our mock_query_job
        mock_client.query.return_value = mock_query_job
        # The .to_dataframe() call on that job returns mock_df
        mock_query_job.to_dataframe.return_value = mock_df

        # Call the DAO
        results = read_workouts()

        # Now results is a DataFrame:
        self.assertEqual(len(results), 2)
        self.assertEqual(results.loc[0, "workout_type"], "pushups")
        self.assertEqual(results.loc[1, "workout_type"], "running")

    @patch("dao.workout_dao.get_bq_client")
    def test_read_workouts_filter(self, mock_get_client: MagicMock) -> None:
        """Test reading workouts with a specific workout_type filter."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_query_job = MagicMock()
        mock_df = pd.DataFrame([
            {"workout_type": "pushups", "date": date(2025, 4, 7), "amount": 25.0, "unit": "reps"}
        ])
        mock_client.query.return_value = mock_query_job
        mock_query_job.to_dataframe.return_value = mock_df

        results = read_workouts("pushups")
        self.assertEqual(len(results), 1)
        self.assertEqual(results.loc[0, "workout_type"], "pushups")

        # confirm that the query was called with the param
        called_query = mock_client.query.call_args[0][0]
        self.assertIn("WHERE workout_type = @filter_type", called_query)


if __name__ == "__main__":
    unittest.main()
