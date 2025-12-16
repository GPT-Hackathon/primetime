import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
import asyncio

# Set env var for testing to avoid valid project check failure if any
os.environ["GCP_PROJECT_ID"] = "test-project"

from agents.validation.validation_agent import validate_data, validation_agent

class TestValidationAgent(unittest.TestCase):

    @patch("agents.validation.validation_agent.bigquery.Client")
    def test_validate_data_report_mode(self, mock_bq_client):
        # Setup Mock
        mock_client_instance = MagicMock()
        mock_bq_client.return_value = mock_client_instance

        # Configure mock job for query results
        mock_job = MagicMock()
        mock_job.num_dml_affected_rows = 3
        mock_client_instance.query.return_value = mock_job

        # Test Data
        rules = [{"column": "test_col", "type": "NOT_NULL"}]
        rules_str = json.dumps(rules)
        table_id = "test-project.dataset.table"

        # Run Function
        result_json = validate_data(table_id, rules_str, "REPORT")
        result = json.loads(result_json)

        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "REPORT")
        self.assertEqual(result["errors_found"], 3)

        # Verify BQ calls
        # 1. Create errors table check
        mock_client_instance.create_table.assert_called()

        # 2. Query execution (Report)
        mock_client_instance.query.assert_called()
        # Verify result was fetched
        mock_job.result.assert_called()

    @patch("agents.validation.validation_agent.bigquery.Client")
    def test_validate_data_fix_mode(self, mock_bq_client):
        # Setup Mock
        mock_client_instance = MagicMock()
        mock_bq_client.return_value = mock_client_instance
        mock_job = MagicMock()
        mock_job.num_dml_affected_rows = 5
        mock_client_instance.query.return_value = mock_job

        # Test Data
        rules = [{"column": "test_col", "type": "NOT_NULL"}]
        rules_str = json.dumps(rules)
        table_id = "test-project.dataset.table"

        # Run Function
        result_json = validate_data(table_id, rules_str, "FIX")
        result = json.loads(result_json)

        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "FIX")
        self.assertEqual(result["rows_corrected"], 5)

        # Verify Update Query was called
        self.assertTrue(mock_client_instance.query.called)
        args, _ = mock_client_instance.query.call_args
        self.assertIn("UPDATE", args[0])
        # Default value should be 0 for non-string columns
        self.assertIn("SET test_col = 0", args[0])

    def test_agent_structure(self):
        # Verify agent is configured correctly
        self.assertEqual(validation_agent.name, "validation_agent")
        self.assertEqual(validation_agent.model, "gemini-2.5-flash")
        self.assertTrue(len(validation_agent.tools) > 0)
        self.assertEqual(validation_agent.tools[0], validate_data)

    @patch("agents.validation.validation_agent.bigquery.Client")
    def test_validate_data_range_check(self, mock_bq_client):
        # Setup Mock
        mock_client_instance = MagicMock()
        mock_bq_client.return_value = mock_client_instance
        mock_job = MagicMock()
        mock_job.num_dml_affected_rows = 3
        mock_client_instance.query.return_value = mock_job

        # Test Data - RANGE validation
        rules = [{"column": "year", "type": "RANGE", "min": 1900, "max": 2100}]
        rules_str = json.dumps(rules)
        table_id = "test-project.dataset.table"

        # Run in REPORT mode
        result_json = validate_data(table_id, rules_str, "REPORT")
        result = json.loads(result_json)

        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "REPORT")
        self.assertTrue(mock_client_instance.query.called)

        # Check that the INSERT query includes range conditions
        args, _ = mock_client_instance.query.call_args
        self.assertIn("INSERT", args[0])

    @patch("agents.validation.validation_agent.bigquery.Client")
    def test_validate_data_range_fix_skipped(self, mock_bq_client):
        # Setup Mock
        mock_client_instance = MagicMock()
        mock_bq_client.return_value = mock_client_instance

        # Test Data - RANGE validation in FIX mode
        rules = [{"column": "year", "type": "RANGE", "min": 1900, "max": 2100}]
        rules_str = json.dumps(rules)
        table_id = "test-project.dataset.table"

        # Run in FIX mode
        result_json = validate_data(table_id, rules_str, "FIX")
        result = json.loads(result_json)

        # Assertions - RANGE fixes should be skipped
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "FIX")
        self.assertEqual(result["rows_corrected"], 0)

    @patch("agents.validation.validation_agent.bigquery.Client")
    def test_validate_data_invalid_json(self, mock_bq_client):
        # Test with invalid JSON
        result_json = validate_data("test.table", "invalid{json", "REPORT")
        result = json.loads(result_json)

        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid rules JSON", result["message"])

    @patch("agents.validation.validation_agent.bigquery.Client")
    def test_validate_data_string_column_fix(self, mock_bq_client):
        # Setup Mock
        mock_client_instance = MagicMock()
        mock_bq_client.return_value = mock_client_instance
        mock_job = MagicMock()
        mock_job.num_dml_affected_rows = 2
        mock_client_instance.query.return_value = mock_job

        # Test Data - NOT_NULL on string column
        rules = [{"column": "country_code", "type": "NOT_NULL"}]
        rules_str = json.dumps(rules)
        table_id = "test-project.dataset.table"

        # Run Function
        result_json = validate_data(table_id, rules_str, "FIX")
        result = json.loads(result_json)

        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["rows_corrected"], 2)

        # Verify string columns get 'UNKNOWN' default
        args, _ = mock_client_instance.query.call_args
        self.assertIn("'UNKNOWN'", args[0])

if __name__ == "__main__":
    unittest.main()
