import unittest
import os
import sys
import litellm # Import litellm

# Add the parent directory to the sys.path to allow importing app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.lmstudio import LMStudioService, LMStudioLiteLLMWrapper # Import the wrapper and service

# Enable LiteLLM debugging for detailed output (optional, can be noisy)
# litellm._turn_on_debug()

class TestLMStudioConnection(unittest.TestCase):

    def setUp(self):
        """Set up test environment before each test method."""
        # Explicitly set LiteLLM API base and key for the test environment
        litellm.api_base = os.getenv("LMSTUDIO_API_BASE_URL", "http://localhost:1234/v1")
        litellm.api_key = "sk-test"  # Dummy key required by LiteLLM
        print(f"\n--- Setting up LiteLLM API base: {litellm.api_base} ---")


    def test_connection_with_wrapper(self):
        """
        Tests if a connection to LM Studio can be established using the LMStudioLiteLLMWrapper.
        """
        print("\n--- Running TestLMStudioConnection.test_connection_with_wrapper ---")
        try:
            # Initialize the LMStudioService (uses default api_base and model_name from env or defaults)
            # Note: LMStudioService also sets global litellm settings, but we explicitly set them in setUp for clarity/override
            api_base = os.getenv("LMSTUDIO_API_BASE_URL", "http://localhost:1234/v1")
            api_key = "sk-test" # Dummy key required by LiteLLM
            lmstudio_service = LMStudioService(api_base=api_base)
            print(f"LMStudioService initialized with API base: {lmstudio_service.api_base}")

            # Initialize the LMStudioLiteLLMWrapper
            llm_wrapper = LMStudioLiteLLMWrapper(lmstudio_service=lmstudio_service)
            print("LMStudioLiteLLMWrapper initialized.")

            # Attempt to call the wrapper with a simple prompt
            prompt = "Hello, what is the capital of France?"
            print(f"Attempting to call wrapper with prompt: {prompt}")
            response = llm_wrapper._call(prompt) # Use _call as it's the core method
            print(f"Wrapper call successful. Response (first 50 chars): {response[:50]}...")

            # Assert that a non-empty response was received and it doesn't indicate an error
            self.assertIsNotNone(response)
            self.assertGreater(len(response), 0)
            self.assertFalse(response.strip().lower().startswith("error:"))
            print("Test passed: Received a valid response from the LLM wrapper.")

        except Exception as e:
            # If any unexpected exception occurs, fail the test
            print(f"Caught unexpected exception during LLM wrapper call: {type(e).__name__}: {e}")
            self.fail(f"Unexpected exception occurred: {type(e).__name__}: {e}")

# This allows running the test directly from the command line
if __name__ == '__main__':
    unittest.main()
