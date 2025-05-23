import logging
import json
from crewai import Agent # Import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field # Ensure this import is present and correct
from typing import Dict, Any, Optional, Union # Import Optional and Union
from app.services.lmstudio import LMStudioService # Assuming LMStudioService is correctly imported
# Assuming CategoryAnalysisResult might be needed for type hinting if you re-introduce process method
# from app.models.response import CategoryAnalysisResult 

logger = logging.getLogger(__name__)

# Define the Pydantic model for the actual input data fields
class CategoryBreakdownInputData(BaseModel):
    """Schema for the actual data fields within the tool's input."""
    prompt: str = Field(description="The original text prompt from the user.")
    topic_analysis: str = Field(description="The JSON string output from the Topic Analysis Tool.")

# Define the Pydantic model that CrewBase seems to expect for args_schema
# This model has a single field named 'tool_input'
class CategoryBreakdownToolInput(BaseModel):
    """Input schema for the CategoryBreakdownTool, structured to satisfy CrewBase validation."""
    # This 'tool_input' field is added to satisfy CrewBase's specific validation
    # The actual data the tool needs is nested within this field.
    tool_input: CategoryBreakdownInputData = Field(description="Container for the tool's input data.")


# Define the custom tool by subclassing BaseTool
class CategoryBreakdownTool(BaseTool):
    """Tool for breaking down a prompt into categories using LMStudio."""

    name: str = "Category Breakdown Tool"
    description: str = (
        "Analyzes a given text prompt and a topic analysis result to break down the prompt "
        "into distinct categories or sub-topics. Returns a JSON array of strings."
        "Input should be a JSON object with a single key 'tool_input', whose value is a JSON object "
        "with 'prompt' (original prompt string) and 'topic_analysis' (Topic Analysis JSON string) keys."
        "Example input JSON: {'tool_input': {'prompt': 'Original Prompt Here', 'topic_analysis': '{...Topic Analysis JSON...}'}"
    )
    # Define the input model for the tool, using the nested structure
    args_schema: type = CategoryBreakdownToolInput

    # Add service and llm as attributes that will be passed during instantiation
    lmstudio_service: LMStudioService
    llm: Any # Or a more specific type if available

    # The _run method now receives the validated CategoryBreakdownToolInput instance
    # Access the actual data from the nested 'tool_input' attribute
    def _run(self, tool_input: Union[CategoryBreakdownToolInput, Dict[str, Any], str]) -> str:
        """
        Runs the category breakdown logic by prompting LMStudio.
        This method is called by the CrewAI agent when the tool is used.
        Receives input as a CategoryBreakdownToolInput instance with nested data,
        a dictionary, or a JSON string.
        """
        logger.info(f"Executing Category Breakdown Tool...")
        
        # --- Safely extract prompt and topic_analysis from tool_input ---
        prompt_content = ""
        topic_analysis_result_str = ""
        parsed_input_data: Optional[Dict[str, Any]] = None

        try:
            if isinstance(tool_input, str):
                logger.info("Tool received string input, attempting JSON parse.")
                parsed_input_data = json.loads(tool_input)
            elif isinstance(tool_input, dict):
                logger.info("Tool received dictionary input.")
                parsed_input_data = tool_input
            elif isinstance(tool_input, CategoryBreakdownToolInput):
                logger.info("Tool received Pydantic model input.")
                parsed_input_data = tool_input.model_dump()
            else:
                logger.error(f"Tool received unexpected input type: {type(tool_input)}")
                return json.dumps({"status": "error", "message": f"Tool received unexpected input type: {type(tool_input)}"})

            if parsed_input_data and 'tool_input' in parsed_input_data and isinstance(parsed_input_data['tool_input'], dict):
                prompt_content = parsed_input_data['tool_input'].get('prompt', '')
                topic_analysis_result_str = parsed_input_data['tool_input'].get('topic_analysis', '')
            else:
                logger.error(f"Could not find 'tool_input' or required keys ('prompt', 'topic_analysis') in parsed input: {parsed_input_data}")
                return json.dumps({"status": "error", "message": "Invalid structure in tool input: missing 'tool_input' or required keys."})

            if not prompt_content:
                logger.error("Tool received empty prompt_content after extraction.")
                return json.dumps({"status": "error", "message": "Tool received empty prompt content."})
            if not topic_analysis_result_str:
                logger.error("Tool received empty topic_analysis_result_str after extraction.")
                return json.dumps({"status": "error", "message": "Tool received empty topic analysis result."})

            logger.info(f"  Prompt (extracted): {prompt_content[:100]}...")
            logger.info(f"  Topic Analysis (extracted): {topic_analysis_result_str[:100]}...")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tool input string as JSON: {e}")
            return json.dumps({"status": "error", "message": f"Tool received invalid JSON string input: {e}"})
        except Exception as e:
            logger.error(f"Error extracting data from tool input: {e}")
            return json.dumps({"status": "error", "message": f"Error processing tool input: {e}"})
        # --- End of input extraction ---


        # Construct prompt for LMStudio
        breakdown_prompt = f"""
Break down the following original prompt into distinct categories or sub-topics.
Consider the topic analysis provided.

Original Prompt: {prompt_content}

Topic Analysis: {topic_analysis_result_str}

List the categories as a JSON array of strings.
Example output: ["Category 1", "Category 2", "Sub-topic A"]
Ensure the output is valid JSON and contains only the JSON array.
"""

        try:
            # Use the LMStudio service instance passed to the tool
            response = self.lmstudio_service.generate_completion(breakdown_prompt)
            logger.info(f"Received response from LMStudio (first 50 chars): {response[:50]}...")

            # Attempt to parse the response to ensure it's valid JSON array before returning
            try:
                # Clean up potential extra text before/after JSON array from LLM
                # Find the first '[' and last ']' to extract the JSON string
                json_start = response.find('[')
                json_end = response.rfind(']')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_string = response[json_start : json_end + 1]
                    # Validate JSON is an array
                    parsed_json = json.loads(json_string)
                    if isinstance(parsed_json, list):
                        return json_string # Return the cleaned JSON array string
                    else:
                        logger.error(f"LMStudio returned valid JSON but not an array: {response}")
                        return json.dumps({"status": "error", "message": "Tool received valid JSON but not an array", "raw_response": response})
                else:
                     logger.error(f"LMStudio response does not contain a valid JSON array structure: {response}")
                     return json.dumps({"status": "error", "message": "Tool received response without valid JSON array structure", "raw_response": response})

            except json.JSONDecodeError:
                logger.error(f"LMStudio returned invalid JSON from tool: {response}")
                # Return an error indicator or formatted message if JSON is invalid
                return json.dumps({"status": "error", "message": "Tool received invalid JSON from LLM", "raw_response": response})

        except Exception as e:
            logger.error(f"Error calling LMStudio service from tool: {e}")
            # Return an error message in a consistent format
            return json.dumps({"status": "error", "message": f"Tool execution failed: {e}"})


class CategoryBreakdownAgent:
    """Agent responsible for breaking down prompts into categories."""

    def __init__(self, config: Dict[str, Any], lmstudio_service: LMStudioService, llm: Any):
        self.config = config
        self.lmstudio_service = lmstudio_service
        self.llm = llm

        # Instantiate the custom tool, passing necessary dependencies
        self.category_breakdown_tool = CategoryBreakdownTool(
            lmstudio_service=self.lmstudio_service,
            llm=self.llm
        )

        # Initialize the CrewAI Agent using the config
        self.agent = Agent(
            role=config.get("role", "Category Breakdown Specialist"),
            goal=config.get("goal", "Break down user prompts into distinct categories and sub-topics."),
            backstory=config.get("backstory", "An expert in organizing complex information into logical categories."),
            verbose=config.get("verbose", False),
            allow_delegation=config.get("allow_delegation", False),
            max_iter=config.get("max_iter", 15),
            max_rpm=config.get("max_rpm", 100),
            llm=self.llm,
            tools=[self.category_breakdown_tool]
        )
