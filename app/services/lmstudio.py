# import lmstudio as lms # Removed - we will use LiteLLM directly
import os
import requests
import subprocess # Import subprocess for lms command
from typing import Dict, Any, Optional, Iterator # Added Iterator
import logging # Import logging
from litellm import completion # Import LiteLLM completion function
from litellm.exceptions import AuthenticationError, APIConnectionError # Import specific LiteLLM exceptions
from langchain_core.language_models.llms import BaseLLM # Import BaseLLM
from langchain_core.outputs import LLMResult, Generation, GenerationChunk # Added GenerationChunk
from typing import List # Import List
import litellm # Import litellm at the top level for type hinting CustomStreamWrapper
import time # Import the time module for delays

# Configure logger for this module
logger = logging.getLogger(__name__)
# Set logging level to DEBUG to see all chunk details
logger.setLevel(logging.DEBUG)
# Add a handler to output to console if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Enable LiteLLM's internal debugging using environment variable as suggested
os.environ['LITELLM_LOG'] = 'DEBUG'
# Removed litellm._turn_on_debug() as it's not exported from the module


def _clean_llm_output(text: str) -> str:
    """
    Cleans the LLM output by removing common unwanted wrapping characters
    like curly braces or triple quotes/backticks.
    """
    if not isinstance(text, str):
        logger.debug(f"Cleaning skipped: Input is not a string (type: {type(text)}).")
        return text # Return as is if not a string

    cleaned_text = text.strip()
    original_text = cleaned_text

    # Remove leading/trailing triple quotes/backticks (common for code blocks)
    # Check for specific languages first, then generic
    code_block_starters = ["```python", "```json", "```text", "```", "'''"]
    code_block_enders = ["```", "'''"]

    for starter in code_block_starters:
        if cleaned_text.startswith(starter):
            logger.debug(f"Cleaning: Removing starter '{starter}'.")
            cleaned_text = cleaned_text[len(starter):].strip()
            # Check for corresponding ender
            for ender in code_block_enders:
                if cleaned_text.endswith(ender):
                    logger.debug(f"Cleaning: Removing ender '{ender}'.")
                    cleaned_text = cleaned_text[:-len(ender)].strip()
                    break # Found an ender, stop checking
            break # Found a starter, stop checking

    # Remove leading/trailing curly braces if they enclose the entire string
    # This is a heuristic and might need adjustment if valid JSON is expected
    if cleaned_text.startswith('{') and cleaned_text.endswith('}'):
        # Simple check: if it's not a complex JSON structure (e.g., just one pair of braces)
        # and doesn't look like a valid JSON object with multiple keys/values
        # This is a simplification; for robust JSON parsing, use json.loads and json.dumps.
        # For this problem, we assume simple unwanted wrappers.
        if cleaned_text.count('{') == 1 and cleaned_text.count('}') == 1:
            logger.debug("Cleaning: Removing outer curly braces.")
            cleaned_text = cleaned_text[1:-1].strip()
        # else:
        #     logger.debug("Cleaning: Keeping curly braces, looks like complex JSON.")

    if original_text != cleaned_text:
        logger.debug(f"Cleaning: Original '{original_text[:50]}...' -> Cleaned '{cleaned_text[:50]}...'.")
    else:
        logger.debug("Cleaning: No changes made to output.")

    return cleaned_text


class LMStudioService:
    """Service for interacting with LMStudio local LLM using LiteLLM"""

    def __init__(self, model_name: Optional[str] = None, api_base: Optional[str] = None):
        # Load API base from environment variable or use default
        self.api_base = api_base if api_base is not None else os.getenv("LMSTUDIO_API_BASE_URL", "http://localhost:1234")
        # Load model name from environment variable or use default
        self.model_name = model_name if model_name is not None else os.getenv("LMSTUDIO_MODEL_NAME", "qwen3-8b")

        # LiteLLM often requires an API key even for local endpoints.
        # A dummy key like "sk-test" or "dummy" usually works.
        self.api_key = "sk-test" # Use a dummy API key

        # Set the global LiteLLM API base to ensure requests go to LMStudio
        litellm.api_base = f"{self.api_base}/v1"
        litellm.api_key = self.api_key # Also set global API key

        # Override the model cost map URL to use our local file instead of GitHub
        model_cost_map_path = "/home/adam/LLM/Prompt_Maker/model_mapping.patch.json"
        if os.path.exists(model_cost_map_path):
            logger.info(f"Using local model cost map from {model_cost_map_path}")
            litellm.model_cost_map_url = f"file://{model_cost_map_path}"
        else:
            logger.warning(f"Local model cost map file not found at {model_cost_map_path}. Will use GitHub URL.")

        # Ensure the model is loaded when the service is initialized
        self.ensure_model_loaded()

    def ensure_model_loaded(self):
        """
        Ensures the specified model is loaded in LMStudio.
        Raises an error if the model is not found or cannot be loaded after retries.
        """
        models_url = f"{self.api_base}/v1/models"
        max_retries = 5
        retry_delay_seconds = 5 # Start with 5 seconds, can increase if needed

        for attempt in range(1, max_retries + 1):
            logger.info(f"Attempt {attempt}/{max_retries}: Checking LMStudio for model '{self.model_name}'.")
            model_found_in_lmstudio = False
            loaded_models = []

            try:
                # 1. Check if LMStudio API is accessible and get loaded models
                response = requests.get(models_url, timeout=5) # Add a timeout
                response.raise_for_status()
                models_data = response.json()
                loaded_models = [model["id"] for model in models_data.get("data", [])]

                self._model_loaded = False
                if self.model_name in loaded_models:
                    logger.info(f"Model '{self.model_name}' is already loaded in LMStudio.")
                    self._model_loaded = True
                    break # Model found, exit retry loop
                else:
                    logger.warning(f"Model '{self.model_name}' not found in LMStudio's currently loaded models. Attempting to load using 'lms' CLI (if not already tried).")
                    # 2. Attempt to load the model using lms CLI (only on first attempt or if explicitly needed)
                    if attempt == 1: # Only try to load via CLI on the first attempt
                        try:
                            logger.info(f"Attempting 'lms load {self.model_name}'...")
                            result = subprocess.run(
                                ["lms", "load", self.model_name],
                                check=True,
                                capture_output=True,
                                text=True,
                                timeout=60 # Generous timeout for loading
                            )
                            logger.info(f"Model '{self.model_name}' load command stdout: {result.stdout}")
                            if result.stderr:
                                logger.warning(f"Model '{self.model_name}' load command stderr: {result.stderr}")
                            # After CLI load, we'll let the next retry check if it's actually loaded
                        except FileNotFoundError:
                            logger.error("Error: 'lms' command not found. Cannot load model automatically.")
                            logger.error("Please ensure LMStudio is installed and 'lms' is in your system's PATH.")
                            # If 'lms' command is not found, no point in retrying CLI load
                            break # Exit retry loop, as auto-load won't work
                        except subprocess.CalledProcessError as e:
                            logger.error(f"Error loading model '{self.model_name}' with 'lms load' command (Exit Code: {e.returncode}): {e.stderr}")
                            logger.error("This often means the model is not downloaded, corrupted, or LMStudio is not running correctly.")
                            # Continue to next retry, as LMStudio might recover or load it later
                        except subprocess.TimeoutExpired:
                            logger.error(f"Error: 'lms load {self.model_name}' command timed out.")
                            # Continue to next retry
                        except Exception as e:
                            logger.error(f"An unexpected error occurred during 'lms load' attempt: {e}")
                            # Continue to next retry

            except requests.exceptions.ConnectionError:
                logger.warning(f"Could not connect to LMStudio API at {models_url} on attempt {attempt}. Retrying in {retry_delay_seconds} seconds...")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error querying LMStudio models endpoint on attempt {attempt}: {e}. Retrying in {retry_delay_seconds} seconds...")
            except Exception as e:
                logger.warning(f"An unexpected error occurred during model check on attempt {attempt}: {e}. Retrying in {retry_delay_seconds} seconds...")

            if not model_found_in_lmstudio and attempt < max_retries:
                time.sleep(retry_delay_seconds)
            elif not model_found_in_lmstudio and attempt == max_retries:
                # If we reach here, all retries failed
                raise ValueError(
                    f"LMStudio model '{self.model_name}' not found or unable to load after {max_retries} attempts. "
                    f"Please ensure LMStudio is running, the model is downloaded, "
                    f"and the model name in your .env (LMSTUDIO_MODEL_NAME) matches "
                    f"the model ID in LMStudio exactly. Currently loaded models: {loaded_models}"
                ) from None

        if not hasattr(self, '_model_loaded') or not self._model_loaded:
            # This block is reached if the 'break' statement was not hit,
            # meaning the model was never found or a critical error occurred that stopped retries.
            raise RuntimeError(
                f"Failed to ensure LMStudio model '{self.model_name}' is loaded. "
                "Check previous logs for more details on connection errors or loading failures."
            )


    def generate_completion(self, prompt: str, temperature: float = 0.7, **kwargs) -> str:
        """Generate text completion using LiteLLM configured for LMStudio"""
        logger.info(f"Service: Generating completion for prompt (first 50 chars): {prompt[:50]}...")
        max_llm_retries = 3
        llm_retry_delay_seconds = 2 # Shorter delay for inference retries

        for attempt in range(1, max_llm_retries + 1):
            try:
                # Prepare kwargs, ensuring 'stream' is not present to avoid conflicts
                call_kwargs = {k: v for k, v in kwargs.items() if k != 'stream'}
                
                response_stream = completion(
                    model=f"openai/{self.model_name}",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    stream=True, # Explicitly force streaming
                    **call_kwargs # Pass other kwargs
                )
                logger.info(f"Service: LiteLLM completion initiated successfully (streaming) on attempt {attempt}.")

                content = ""
                for chunk in response_stream:
                    if chunk is None:
                        logger.warning("Service: Received None as chunk in streaming response")
                        continue

                    logger.debug(f"Service: Raw Streaming Chunk: {chunk}") # Log the raw chunk for inspection

                    try:
                        # First try to handle dict-based structure
                        if isinstance(chunk, dict):
                            choices = chunk.get('choices')
                            if choices and isinstance(choices, list) and len(choices) > 0:
                                choice = choices[0]
                                logger.debug(f"Service: Extracted Choice: {choice}")
                                if isinstance(choice, dict):
                                    delta = choice.get('delta')
                                    if delta and isinstance(delta, dict):
                                        # Try to get content from various possible locations
                                        content_part = delta.get('content') or getattr(delta, 'content', None)
                                        if content_part:
                                            content += content_part
                                            logger.debug(f"Service: Appended Content Part. Current length: {len(content)}")

                                        # Also check for reasoning_content which might contain text
                                        reasoning_content = delta.get('reasoning_content') or getattr(delta, 'reasoning_content', None)
                                        if reasoning_content:
                                            content += reasoning_content
                                            logger.debug(f"Service: Appended Reasoning Content. Current length: {len(content)}")
                                else:
                                    logger.debug("Service: 'delta' is not a dictionary.")
                            else:
                                logger.debug("Service: Choice is not a dictionary or is empty.")
                        else:
                            # Handle non-dict chunks - this includes ModelResponseStream and other types
                            logger.debug(f"Service: Non-dict chunk type: {type(chunk)}")

                            # Special handling for ModelResponseStream objects
                            if hasattr(chunk, 'choices') and isinstance(getattr(chunk, 'choices'), list) and len(getattr(chunk, 'choices')) > 0:
                                choice = getattr(chunk, 'choices')[0]
                                logger.debug(f"Service: Extracted choice from ModelResponseStream: {choice}")

                                # Handle delta content in the choice
                                if hasattr(choice, 'delta') and getattr(choice, 'delta') is not None:
                                    delta = getattr(choice, 'delta')

                                    # Try to get content from various possible locations
                                    if hasattr(delta, 'content'):
                                        content_part = getattr(delta, 'content')
                                        if content_part:
                                            content += str(content_part)
                                            logger.debug(f"Service: Extracted content from ModelResponseStream delta. Current length: {len(content)}")

                                    # Also check for reasoning_content which might contain text
                                    if hasattr(delta, 'reasoning_content'):
                                        reasoning_content = getattr(delta, 'reasoning_content')
                                        if reasoning_content:
                                            content += str(reasoning_content)
                                            logger.debug(f"Service: Extracted reasoning_content from ModelResponseStream delta. Current length: {len(content)}")
                            # Handle other non-dict objects with content attributes
                            elif hasattr(chunk, 'content'):
                                content_part = getattr(chunk, 'content', None)
                                if content_part:
                                    content += str(content_part)
                                    logger.debug(f"Service: Extracted content attribute. Current length: {len(content)}")

                            # Check for reasoning_content on the chunk itself
                            if hasattr(chunk, 'reasoning_content'):
                                reasoning_content = getattr(chunk, 'reasoning_content', None)
                                if reasoning_content:
                                    content += str(reasoning_content)
                                    logger.debug(f"Service: Extracted reasoning_content. Current length: {len(content)}")
                    except Exception as e:
                        logger.debug(f"Service: Error processing chunk: {str(e)}")

                if content: # If content is successfully extracted, break from retry loop
                    cleaned_content = _clean_llm_output(content)
                    return cleaned_content
                else:
                    logger.warning(f"Service: No content extracted from LLM streaming response on attempt {attempt}. Retrying...")
                    if attempt < max_llm_retries:
                        time.sleep(llm_retry_delay_seconds)
                    else:
                        logger.error(f"Service: Failed to get content after {max_llm_retries} attempts.")
                        raise ValueError("No content extracted from LLM streaming response after multiple retries.")

            except (AuthenticationError, APIConnectionError) as e:
                logger.error(f"Service: LiteLLM Authentication or Connection Error on attempt {attempt}: {e}")
                if attempt < max_llm_retries:
                    time.sleep(llm_retry_delay_seconds)
                else:
                    raise e # Re-raise after all retries
            except Exception as e:
                logger.error(f"Service: An unexpected error occurred during LiteLLM completion on attempt {attempt}: {e}")
                if attempt < max_llm_retries:
                    time.sleep(llm_retry_delay_seconds)
                else:
                    raise e # Re-raise after all retries
        # This line should ideally not be reached if retries are handled correctly
        raise RuntimeError("Unexpected state: generate_completion did not return or raise an exception.")


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
        # Return the model name in the format expected by LiteLLM/CrewAI
        return f"openai/{self._lmstudio_service.model_name}"

    def _stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        """Stream the LLM response."""
        logger.info(f"Wrapper: _stream for prompt (first 50 chars): {prompt[:50]}...")
        max_llm_retries = 3
        llm_retry_delay_seconds = 2

        for attempt in range(1, max_llm_retries + 1):
            try:
                # Prepare kwargs, ensuring 'stream' is not present to avoid conflicts
                call_kwargs = {k: v for k, v in kwargs.items() if k != 'stream'}

                response_stream = completion(
                    model=f"openai/{self._lmstudio_service.model_name}",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=kwargs.get("temperature", 0.7),
                    stop=stop,
                    stream=True, # Force streaming here
                    **call_kwargs # Pass other kwargs
                )
                logger.info(f"Wrapper: LiteLLM streaming initiated successfully on attempt {attempt}.")

                # Yield chunks directly
                for chunk in response_stream:
                    logger.debug(f"Wrapper: Raw Streaming Chunk (Stream): {chunk}")
                    if isinstance(chunk, dict):
                        choices = chunk.get('choices')
                        if choices and isinstance(choices, list) and len(choices) > 0:
                            choice = choices[0]
                            if isinstance(choice, dict):
                                delta = choice.get('delta')
                                if delta and isinstance(delta, dict):
                                    content_part = delta.get('content')
                                    reasoning_content_part = delta.get('reasoning_content')
                                    
                                    extracted_text = ""
                                    if content_part is not None:
                                        extracted_text += str(content_part)
                                    if reasoning_content_part is not None:
                                        extracted_text += str(reasoning_content_part)

                                    if extracted_text:
                                        yield GenerationChunk(text=extracted_text)
                                    else:
                                        logger.debug(f"Wrapper: No content or reasoning_content in delta. Delta: {delta} (Stream).")
                                else:
                                    logger.debug("Wrapper: 'delta' is not a dictionary or is None (Stream).")
                            else:
                                logger.debug("Wrapper: Choice is not a dictionary (Stream).")
                        else:
                            logger.debug("Wrapper: 'choices' is not a list, is empty, or is None (Stream).")
                    else:
                        logger.debug(f"Wrapper: Non-dict chunk type (Stream): {type(chunk)}")

                        extracted_text = ""
                        # Special handling for ModelResponseStream objects
                        if hasattr(chunk, 'choices') and isinstance(getattr(chunk, 'choices'), list) and len(getattr(chunk, 'choices')) > 0:
                            choice = getattr(chunk, 'choices')[0]
                            logger.debug(f"Wrapper: Extracted choice from ModelResponseStream (Stream): {choice}")

                            # Handle delta content in the choice
                            if hasattr(choice, 'delta') and getattr(choice, 'delta') is not None:
                                delta = getattr(choice, 'delta')

                                # Try to get content from various possible locations
                                if hasattr(delta, 'content'):
                                    content_part = getattr(delta, 'content')
                                    if content_part:
                                        extracted_text += str(content_part)
                                        logger.debug(f"Wrapper: Extracted content from ModelResponseStream delta (Stream).")

                                # Also check for reasoning_content which might contain text
                                if hasattr(delta, 'reasoning_content'):
                                    reasoning_content = getattr(delta, 'reasoning_content')
                                    if reasoning_content:
                                        extracted_text += str(reasoning_content)
                                        logger.debug(f"Wrapper: Extracted reasoning_content from ModelResponseStream delta (Stream).")
                        # Handle other non-dict objects with content attributes
                        elif hasattr(chunk, 'content'):
                            content_part = getattr(chunk, 'content', None)
                            if content_part:
                                extracted_text += str(content_part)
                                logger.debug(f"Wrapper: Extracted content attribute (Stream).")

                        # Check for reasoning_content on the chunk itself
                        if hasattr(chunk, 'reasoning_content'):
                            reasoning_content = getattr(chunk, 'reasoning_content', None)
                            if reasoning_content:
                                extracted_text += str(reasoning_content)
                                logger.debug(f"Wrapper: Extracted reasoning_content (Stream).")
                        
                        if extracted_text:
                            yield GenerationChunk(text=extracted_text)
                        else:
                            logger.debug(f"Wrapper: No content extracted from non-dict chunk: {chunk} (Stream).")
                return # Successfully streamed, exit retry loop

            except Exception as e:
                logger.error(f"Wrapper: Error during LMStudioLiteLLMWrapper _stream on attempt {attempt}: {e}")
                if attempt < max_llm_retries:
                    time.sleep(llm_retry_delay_seconds)
                else:
                    raise e # Re-raise after all retries

        raise RuntimeError("Unexpected state: _stream did not complete or raise an exception.")


    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        """
        Implement the core logic of the LLM for non-streaming calls.
        This method will collect the full streamed response.
        """
        logger.info(f"Wrapper: _call (non-streaming fallback) for prompt (first 50 chars): {prompt[:50]}...")
        full_response_content = ""
        try:
            # Use the _stream method internally to get chunks and collect them
            for chunk in self._stream(prompt, stop, run_manager, **kwargs):
                full_response_content += chunk.text
            
            if not full_response_content:
                logger.error("Wrapper: No content extracted from LLM (non-streaming fallback).")
                raise ValueError("LLM returned empty or invalid content (non-streaming fallback).")
            
            cleaned_content = _clean_llm_output(full_response_content)
            return cleaned_content

        except Exception as e:
            logger.error(f"Wrapper: Error during LMStudioLiteLLMWrapper _call (non-streaming fallback): {e}")
            raise e


    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Generate completion for the given prompts."""
        logger.info(f"Wrapper: _generate for {len(prompts)} prompts.")
        generations: List[List[Generation]] = []
        for prompt in prompts:
            current_content = ""
            try:
                # Use the _stream method internally for each prompt
                for chunk in self._stream(prompt, stop, run_manager, **kwargs):
                    current_content += chunk.text

                if not current_content:
                    logger.error(f"Wrapper: No content extracted from LLM for prompt: {prompt[:50]}... (in _generate).")
                    generations.append([Generation(text=f"Error: No content from LLM for prompt: {prompt[:50]}...")])
                else:
                    cleaned_content = _clean_llm_output(current_content)
                    generations.append([Generation(text=cleaned_content)])

            except Exception as e:
                logger.error(f"Wrapper: Error during LMStudioLiteLLMWrapper _generate call for prompt: {prompt[:50]}... Error: {e}")
                generations.append([Generation(text=f"Error during LLM call: {e}")])

        return LLMResult(generations=generations)
