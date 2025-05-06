import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime # Import datetime if used in models/agents being tested indirectly
import json # Import json if used in models/agents being tested indirectly
import requests # Import requests to reference exceptions

# Import the functions to be tested
from app.run import check_lmstudio_running, main

class TestRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load environment variables for the test class
        import app.config.env_config
    # Patching targets remain the same now that imports are at the top of app.run
    @patch('app.run.requests.get')
    def test_check_lmstudio_running_success(self, mock_get):
        """Test check_lmstudio_running when LMStudio is running"""
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the function and assert the result
        self.assertTrue(check_lmstudio_running())

        # Verify requests.get was called
        mock_get.assert_called_once_with("http://localhost:1234/v1/models")

    @patch('app.run.requests.get')
    def test_check_lmstudio_running_failure(self, mock_get):
        """Test check_lmstudio_running when LMStudio is not running (connection error)"""
        # Configure the mock to raise a ConnectionError
        mock_get.side_effect = requests.exceptions.ConnectionError # Need to import requests here to reference the exception

        # Call the function and assert the result
        self.assertFalse(check_lmstudio_running())

        # Verify requests.get was called
        mock_get.assert_called_once_with("http://localhost:1234/v1/models")

    # Patch subprocess.Popen, check_lmstudio_running, AND uvicorn.run
    @patch('app.run.uvicorn.run') # <-- Patch uvicorn.run
    @patch('app.run.subprocess.Popen')
    @patch('app.run.check_lmstudio_running', return_value=False) # Mock check_lmstudio_running to return False
    def test_main_starts_lms(self, mock_check, mock_popen, mock_uvicorn_run): # <-- Add mock_uvicorn_run
        """Test that main attempts to start LMS if it's not running"""
        # Call the main function
        main()

        # Assert that check_lmstudio_running was called
        mock_check.assert_called_once()

        # Assert that subprocess.Popen was called with the correct command
        mock_popen.assert_called_once_with(["lms", "server", "start"])

        # Assert that uvicorn.run was called (even though it's mocked)
        mock_uvicorn_run.assert_called_once()


    # Add a test case where LMStudio is already running
    # Patch subprocess.Popen, check_lmstudio_running, AND uvicorn.run
    @patch('app.run.uvicorn.run') # <-- Patch uvicorn.run
    @patch('app.run.subprocess.Popen') # Still patch Popen even if not called
    @patch('app.run.check_lmstudio_running', return_value=True) # Mock check_lmstudio_running to return True
    def test_main_lms_already_running(self, mock_check, mock_popen, mock_uvicorn_run): # <-- Add mock_uvicorn_run
        """Test that main does NOT attempt to start LMS if it's already running"""
        # Call the main function
        main()

        # Assert that check_lmstudio_running was called
        mock_check.assert_called_once()

        # Assert that subprocess.Popen was NOT called
        mock_popen.assert_not_called()

        # Assert that uvicorn.run was called (even though it's mocked)
        mock_uvicorn_run.assert_called_once()

