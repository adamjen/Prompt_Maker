import logging
import json
from crewai import Agent # Import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, Union, Optional # Import Optional
from app.services.lmstudio import LMStudioService # Assuming LMStudioService is correctly imported

logger = logging.getLogger(__name__)

# --- Topic Analysis Tool ---

# Define the Pydantic model for the actual input data fields for the tool
class TopicAnalysisInputData(BaseModel):
    """Schema for the actual data fields within the tool's input."""
    text_to_analyze: str = Field(description="The text content to analyze for topics, domain, complexity, and key entities.")

# Define the Pydantic model that CrewBase seems to expect for args_schema
class TopicAnalysisToolInput(BaseModel):
    """Input schema for the TopicAnalysisTool, structured to satisfy CrewBase validation."""
    tool_input: TopicAnalysisInputData = Field(description="Container for the tool's input data.")

# Define the custom tool by subclassing BaseTool
class TopicAnalysisTool(BaseTool):
    """Tool for analyzing text to identify topics, domain, complexity, and key entities using LMStudio."""

    name: str = "Topic Analysis Tool"
    description: str = (
        "Analyzes input text to extract core topics, domain, complexity, and key entities. "
        "Input should be a JSON object with a single key 'tool_input', whose value is a JSON object "
        "with a 'text_to_analyze' key."
        "Example input JSON: {'tool_input': {'text_to_analyze': 'Text content here'}}"
    )
    # Define the input model for the tool, using the nested structure
    args_schema: type = TopicAnalysisToolInput

    # Add service and llm as attributes that will be passed during instantiation
    lmstudio_service: LMStudioService
    llm: Any # Or a more specific type if available

    # Update the _run method to accept Union[TopicAnalysisToolInput, Dict[str, Any], str]
    def _run(self, tool_input: Union[TopicAnalysisToolInput, Dict[str, Any], str]) -> str:
        """
        Runs the topic analysis logic by prompting LMStudio.
        This method is called by the CrewAI agent when the tool is used.
        Handles input as either a Pydantic model instance, a dictionary, or a JSON string.
        """
        logger.info(f"Executing Topic Analysis Tool...")

        # --- Safely extract text_to_analyze from tool_input ---
        text_to_analyze = ""
        parsed_input_data: Optional[Dict[str, Any]] = None

        try:
            if isinstance(tool_input, str):
                # If input is a string, attempt to parse it as JSON
                logger.info("Tool received string input, attempting JSON parse.")
                parsed_input_data = json.loads(tool_input)
            elif isinstance(tool_input, dict):
                # If input is already a dictionary
                logger.info("Tool received dictionary input.")
                parsed_input_data = tool_input
            elif isinstance(tool_input, TopicAnalysisToolInput):
                # If input is the expected Pydantic model, convert to dict
                logger.info("Tool received Pydantic model input.")
                parsed_input_data = tool_input.model_dump() # Use model_dump for Pydantic v2
            else:
                logger.error(f"Tool received unexpected input type: {type(tool_input)}")
                return json.dumps({"status": "error", "message": f"Tool received unexpected input type: {type(tool_input)}"})

            # Now, extract text_to_analyze from the parsed dictionary
            if parsed_input_data and 'tool_input' in parsed_input_data and isinstance(parsed_input_data['tool_input'], dict):
                text_to_analyze = parsed_input_data['tool_input'].get('text_to_analyze', '')
            else:
                logger.error(f"Could not find 'tool_input' or 'text_to_analyze' in parsed input: {parsed_input_data}")
                return json.dumps({"status": "error", "message": "Invalid structure in tool input: missing 'tool_input' or 'text_to_analyze'."})

            if not text_to_analyze:
                 logger.error("Tool received empty text_to_analyze after extraction.")
                 return json.dumps({"status": "error", "message": "Tool received empty text to analyze."})

            logger.info(f"  Text to Analyze (extracted): {text_to_analyze[:100]}...")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tool input string as JSON: {e}")
            return json.dumps({"status": "error", "message": f"Tool received invalid JSON string input: {e}"})
        except Exception as e:
            logger.error(f"Error extracting text_to_analyze from tool input: {e}")
            return json.dumps({"status": "error", "message": f"Error processing tool input: {e}"})
        # --- End of input extraction ---


        # Construct prompt for LMStudio
        analysis_prompt = f"""
Analyze the following text to identify its core topics, domain, complexity, and key entities.

Text to Analyze: {text_to_analyze}

Provide the output as a JSON object with the following keys:
- core_topics: A list of strings representing the main topics.
- domain: A string representing the subject area (e.g., 'technology', 'science', 'business').
- complexity: A string indicating the complexity ('low', 'medium', 'high').
- key_entities: A list of strings representing important names, places, or concepts.

Ensure the output is valid JSON and contains only the JSON object.
Example output: {{"core_topics": ["topic1", "topic2"], "domain": "example", "complexity": "medium", "key_entities": ["entityA", "entityB"]}}
"""

        try:
            # Use the LMStudio service instance passed to the tool
            response = self.lmstudio_service.generate_completion(analysis_prompt)
            logger.info(f"Received response from LMStudio (first 50 chars): {response[:50]}...")

            # --- Robustly handle and parse the LLM response ---
            if not response or not isinstance(response, str):
                 logger.error("LMStudio returned None, empty, or non-string response.")
                 return json.dumps({"status": "error", "message": "Tool received empty or invalid response from LLM."})

            # Attempt to parse the response to ensure it's valid JSON before returning
            try:
                # Clean up potential extra text before/after JSON object from LLM
                # Find the first '{' and last '}' to extract the JSON string
                json_start = response.find('{')
                json_end = response.rfind('}')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_string = response[json_start : json_end + 1]
                    # Validate JSON is an object
                    parsed_json = json.loads(json_string)
                    if isinstance(parsed_json, dict):
                        # Optional: Validate keys in parsed_json if necessary
                        logger.info("Successfully parsed JSON from LLM response.")
                        return json_string # Return the cleaned JSON object string
                    else:
                        logger.error(f"LMStudio returned valid JSON but not an object: {response}")
                        return json.dumps({"status": "error", "message": "Tool received valid JSON but not an object", "raw_response": response})
                else:
                     logger.error(f"LMStudio response does not contain a valid JSON object structure: {response}")
                     return json.dumps({"status": "error", "message": "Tool received response without valid JSON object structure", "raw_response": response})

            except json.JSONDecodeError:
                logger.error(f"LMStudio returned invalid JSON from tool: {response}")
                # Return an error indicator or formatted message if JSON is invalid
                return json.dumps({"status": "error", "message": "Tool received invalid JSON from LLM", "raw_response": response})
            # --- End of response handling ---

        except Exception as e:
            logger.error(f"Error calling LMStudio service from tool: {e}")
            # Return an error message in a consistent format
            return json.dumps({"status": "error", "message": f"Tool execution failed: {e}"})


class TopicAnalysisAgent:
    """Agent responsible for analyzing the prompt topic."""

    def __init__(self, config: Dict[str, Any], lmstudio_service: LMStudioService, llm: Any):
        self.config = config
        self.lmstudio_service = lmstudio_service # Store the service instance
        self.llm = llm # Store llm

        # Instantiate the custom tool, passing necessary dependencies
        self.topic_analysis_tool = TopicAnalysisTool(
            lmstudio_service=self.lmstudio_service,
            llm=self.llm # Pass the llm to the tool if needed within _run
        )

        # Initialize the CrewAI Agent here using the config
        self.agent = Agent(
            role=config.get("role", "Topic Analysis Specialist"),
            goal=config.get("goal", "Analyze the user's prompt to identify core topics, domain, complexity, and key entities."),
            backstory=config.get("backstory", "An expert in dissecting complex queries into fundamental components."),
            verbose=config.get("verbose", False),
            allow_delegation=config.get("allow_delegation", False),
            max_iter=config.get("max_iter", 15),
            max_rpm=config.get("max_rpm", 100),
            llm=self.llm, # Pass the llm instance to the CrewAI Agent
            tools=[self.topic_analysis_tool] # Assign the instantiated tool to the agent
        )
