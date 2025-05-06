import os
import sys
import unittest

# Add the parent directory to the Python path to allow importing app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

class TestEnvironmentLoading(unittest.TestCase):

    def test_environment_variables_loaded(self):
        # This import should trigger the environment variable loading
        import app.config.env_config

        # Now check the environment variables
        lmstudio_api_base = os.getenv("LMSTUDIO_API_BASE_URL")
        lmstudio_model_name = os.getenv("LMSTUDIO_MODEL_NAME")
        database_url = os.getenv("DATABASE_URL")

        # Assert that the environment variables are loaded (not None)
        self.assertIsNotNone(lmstudio_api_base, "LMSTUDIO_API_BASE_URL should be loaded")
        self.assertIsNotNone(lmstudio_model_name, "LMSTUDIO_MODEL_NAME should be loaded")
        self.assertIsNotNone(database_url, "DATABASE_URL should be loaded")

        # Assert that the environment variables are not the placeholder strings
        self.assertNotEqual(lmstudio_api_base, "your_lmstudio_api_base_url_here", "LMSTUDIO_API_BASE_URL should not be the placeholder")
        self.assertNotEqual(lmstudio_model_name, "your_lmstudio_model_name_here", "LMSTUDIO_MODEL_NAME should not be the placeholder")
        self.assertNotEqual(database_url, "your_database_url_here", "DATABASE_URL should not be the placeholder")

if __name__ == '__main__':
    unittest.main()