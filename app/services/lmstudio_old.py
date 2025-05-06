import os
import requests
import subprocess # Import subprocess for lms command
from typing import Dict, Any, Optional
import logging # Import logging
from litellm import completion # Import LiteLLM completion function
from litellm.exceptions import AuthenticationError, APIConnectionError # Import specific LiteLLM exceptions
from langchain_core.language_models.llms import BaseLLM # Import BaseLLM
from langchain_core.outputs import LLMResult, Generation # Import LLMResult and Generation
from typing import List # Import List

# Load environment variables from .env file

# Configure logger for this module
logger = logging.getLogger(__name__)

class LMStudioService:
    """Service for interacting with LMStudio local LLM using LiteLLM"""

    def __init__(self):
        # Read configuration from environment variables
        self.api_base = os.getenv("LMSTUDIO_API_BASE_URL", "http://localhost:1234/v1")
        self.model_name = os.getenv("LMSTUDIO_MODEL_NAME")
        # LiteLLM often requires an API key even for local endpoints.
        # A dummy key like "sk-test" or "dummy" usually works.
        self.api_key = os.getenv("LMSTUDIO_API_KEY", "sk-test") # Default to "sk-test" if not set

        # Removed setting OPENAI_API_KEY environment variable

        # Removed LiteLLM custom endpoint configuration
        # Removed global api_base and api_key setting to avoid conflicts
        # litellm.api_base = f"{self.api_base}/v1"
        # litellm.api_key = self.api_key # Also set global API key

        # Ensure the model is loaded when the service is initialized
        # Note: This might not be ideal for all scenarios (e.g., if LMStudio
        # is started separately). Consider if this is the right place for this logic.
        # self.ensure_model_loaded() # Commenting out to avoid blocking startup if lms CLI is not set up

    def ensure_model_loaded(self):
        """Ensure the model is loaded in LMStudio"""
        # This method requires the 'lms' command-line tool to be installed and in PATH
        # and assumes LMStudio is running.
        models_url = f"{self.api_base}/v1/models" # Use v1 endpoint for models
        try:
            # Use requests to check if the model is listed
            response = requests.get(models_url)
            response.raise_for_status() # Raise an exception for bad status codes
            models_data = response.json()

            # Check if the model is in the list of available models
            if not any(model["id"] == self.model_name for model in models_data.get("data", [])):
                logger.warning(f"Model '{self.model_name}' not found in LMStudio. Attempting to load using 'lms' CLI...")
                # Use LMStudio CLI to load model
                # Ensure 'lms' is in your system's PATH or provide its full path
                try:
                    # subprocess.run waits for the command to complete
                    # You might need to adjust the command based on your LMStudio installation
                    subprocess.run(["lms", "load", self.model_name], check=True, capture_output=True, text=True) # Use check=True, capture_output, text
                    logger.info(f"Model '{self.model_name}' loaded successfully.")
                except FileNotFoundError:
                    logger.error("Error: 'lms' command not found. Cannot load model automatically.")
                    logger.error("Please ensure LMStudio is running and the model is loaded manually.")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error loading model '{self.model_name}' with 'lms load': {e.stderr}")
                    logger.error("Please check LMStudio logs for more details.")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while attempting to load model: {e}")
                    logger.error("Please ensure LMStudio is running and the model is loaded manually.")
            else:
                logger.info(f"Model '{self.model_name}' is already loaded in LMStudio.")

        except requests.exceptions.ConnectionError:
             logger.error(f"Error: Could not connect to LMStudio API at {models_url}. Please ensure LMStudio is running and the API server is enabled.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking LMStudio models endpoint {models_url}: {e}")
        except Exception as e:
             logger.error(f"An unexpected error occurred while ensuring model is loaded: {e}")


    def generate_completion(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text completion using LiteLLM configured for LMStudio"""
        logger.info(f"Service: Generating completion for prompt (first 50 chars): {prompt[:50]}...")
        response = None # Initialize response to None
        try:
            # Use LiteLLM's completion function
            # Explicitly pass api_base and api_key, and specify the model name
            # Note: With the global api_base set, these might be redundant,
            # but keeping them for clarity and potential future flexibility.
            logger.info(f"Service: Calling LiteLLM completion with model=f'lm_studio/{self.model_name}") # Log parameters
            response = completion(
                model="lm_studio/{self.model_name}", # Use "lm_studio/" prefix for LMStudio
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                api_key=self.api_key, # Explicitly pass the API key
                # Add other parameters as needed, e.g., max_tokens
                # max_tokens=150 # Example: Limit response length
            )
            logger.info("Service: LiteLLM completion successful.")
            # Log the full response object for inspection
            logger.info(f"Service: Raw LiteLLM Response: {response}")

            # Extract the content from the response
            # Check if choices and message exist before accessing content
            if response and response.choices and len(response.choices) > 0 and response.choices[0].message and response.choices[0].message.content is not None:
                 return response.choices[0].message.content
            else:
                 logger.error("Service: Received response from LiteLLM with no content.")
                 # Return a specific error message if content is missing
                 return "Error: Received empty or invalid content from LLM."

        except (AuthenticationError, APIConnectionError) as e:
             logger.error(f"Service: LiteLLM Authentication or Connection Error: {e}")
             # Return an informative error string for known LiteLLM errors
             return f"Error: Failed to connect to LMStudio or authenticate with LiteLLM. Details: {e}"
        except Exception as e:
            logger.error(f"Service: An unexpected error occurred during LiteLLM completion: {e}")
            # Return a generic error message for other exceptions
            return f"Error: An unexpected error occurred during completion. Details: {e}"

class LMStudioLiteLLMWrapper(BaseLLM):
    """
    A wrapper around LMStudioService to make it compatible with LangChain's BaseLLM.
    This allows using LMStudioService directly with frameworks like CrewAI
    that expect a LangChain LLM object.
    """
    _lmstudio_service: LMStudioService # Renamed to private attribute

    def __init__(self, lmstudio_service: LMStudioService, **kwargs: Any):
        super().__init__(**kwargs)
        self._lmstudio_service = lmstudio_service # Assign to the private attribute

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "lmstudio_litellm_wrapper"

    @property
    def model_name(self) -> str:
        """Return the model name used by this LLM."""
        # Return the model name with the "openai/" prefix for LiteLLM compatibility
        return f"lm_studio/{self._lmstudio_service.model_name}"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None, # Use Any for simplicity with CrewAI's run_manager
        **kwargs: Any,
    ) -> str:
        """
        Implement the core logic of the LLM.
        This method is called by the LangChain/CrewAI framework.
        """
        logger.info(f"Wrapper: _call for prompt (first 50 chars): {prompt[:50]}...")
        response = None # Initialize response to None
        try:
            # Directly call LiteLLM completion using the service's configuration
            # Global api_base and api_key should now be set by LMStudioService __init__
            response = completion(
                model="lm_studio/{self.model_name}",
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.7), # Pass temperature from kwargs or default
                stop=stop, # Pass stop words
                api_base=f"{self._lmstudio_service.api_base}/v1", # Explicitly pass api_base
                api_key=self._lmstudio_service.api_key, # Explicitly pass the API key
                **kwargs # Pass any other relevant kwargs
            )
            logger.info("Wrapper: LiteLLM completion successful in wrapper.")
            # Log the full response object for inspection
            logger.info(f"Wrapper: Raw LiteLLM Response: {response}")

            # Check if choices and message exist before accessing content
            if response and response.choices and len(response.choices) > 0 and response.choices[0].message and response.choices[0].message.content is not None:
                 return response.choices[0].message.content
            else:
                 logger.error("Wrapper: Received response from LiteLLM with no content.")
                 # Raise an error if content is missing, as LangChain/CrewAI expects a string here
                 raise ValueError("LLM returned empty or invalid content.")

        except Exception as e:
            logger.error(f"Wrapper: Error during LMStudioLiteLLMWrapper _call: {e}")
            # Re-raise the exception to be handled by the calling framework (CrewAI/LangChain)
            raise e

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None, # Use Any for simplicity
        **kwargs: Any,
    ) -> LLMResult:
        """Generate completion for the given prompts."""
        logger.info(f"Wrapper: _generate for {len(prompts)} prompts.")
        generations: List[List[Generation]] = []
        for prompt in prompts:
            response = None # Initialize response to None per prompt
            try:
                # Directly call LiteLLM completion for each prompt
                # Global api_base and api_key should now be set by LMStudioService __init__
                response = completion(
                    model="lm_studio/{self.model_name}",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=kwargs.get("temperature", 0.7), # Pass temperature from kwargs or default
                    stop=stop, # Pass stop words
                    api_base=f"{self._lmstudio_service.api_base}/v1", # Explicitly pass api_base
                    api_key=self._lmstudio_service.api_key, # Explicitly pass the API key
                    **kwargs # Pass any other relevant kwargs
                    )
                logger.info(f"Wrapper: LiteLLM completion successful for prompt: {prompt[:50]}...")
                # Log the full response object for inspection
                logger.info(f"Wrapper: Raw LiteLLM Response for prompt: {response}")

                # Wrap the response text in a Generation object
                # Check if choices and message exist before accessing content
                if response and response.choices and len(response.choices) > 0 and response.choices[0].message and response.choices[0].message.content is not None:
                    generations.append([Generation(text=response.choices[0].message.content)])
                else:
                    logger.error(f"Wrapper: Received response from LiteLLM with no content for prompt: {prompt[:50]}...")
                    # Append an error generation or handle as appropriate
                    generations.append([Generation(text=f"Error: Received empty or invalid content from LLM for prompt: {prompt[:50]}...")])

            except Exception as e:
                logger.error(f"Wrapper: Error during LMStudioLiteLLMWrapper _generate call for prompt: {prompt[:50]}... Error: {e}")
                # Append an error generation or handle as appropriate
                generations.append([Generation(text=f"Error during LLM call: {e}")])

        # Create an LLMResult object
        # Note: Token usage and other details might not be available or need
        # to be extracted from the underlying LiteLLM response if possible.
        # For simplicity, we'll create a basic LLMResult.
        return LLMResult(generations=generations)
