import unittest
import os
import sys

# Add the parent directory to the sys.path to allow importing app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.lmstudio import LMStudioService, LMStudioLiteLLMWrapper
from app.models.prompt import PromptRequest  # Although not directly used by the wrapper, good to have relevant imports

import litellm  # Import litellm

class TestLMStudioWrapper(unittest.TestCase):

    def test_wrapper_initialization_and_call(self):
        """
        Tests if the LMStudioLiteLLMWrapper can be initialized and called.
        This test verifies connection to the LLM provider.
        """
        print("\n--- Running TestLMStudioWrapper.test_wrapper_initialization_and_call ---")
        # Comment out or remove debugging to reduce log noise
        # litellm._turn_on_debug()  # Disabled to avoid debug log clutter
        try:
            # Initialize the LMStudioService
            # Use default parameters which point to localhost:1234
            lmstudio_service = LMStudioService()
            print("LMStudioService initialized.")

            # Initialize the LMStudioLiteLLMWrapper
            llm_wrapper = LMStudioLiteLLMWrapper(lmstudio_service=lmstudio_service)
            print("LMStudioLiteLLMWrapper initialized.")

            # Attempt to call the wrapper with a simple prompt
            prompt = "Hello, what is the capital of France?"
            print(f"Attempting to call wrapper with prompt: {prompt}")
            response = llm_wrapper._call(prompt)  # Using _call as it's the core method
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
