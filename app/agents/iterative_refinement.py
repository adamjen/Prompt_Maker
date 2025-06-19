import logging
from crewai import Agent
from crewai.tools import BaseTool # Import BaseTool
# Assuming these models exist
from app.models.prompt import PromptRequest # Assuming PromptRequest might be needed for type hinting
from app.models.response import IterativeRefinementResult, TopicAnalysisResult, CategoryAnalysisResult # Import necessary result models
from app.services.lmstudio import LMStudioService # Import LMStudioService
from typing import Dict, Any, Optional
from datetime import datetime
import json # Import json

logger = logging.getLogger(__name__)

# Define the custom tool by subclassing BaseTool
class IterativeRefinementTool(BaseTool):
    """Tool for iteratively refining a prompt using LMStudio."""

    name: str = "Iterative Refinement Tool"
    description: str = (
        "Refines a given original prompt based on provided topic analysis and category breakdown results. "
        "Improves clarity, specificity, and structure. Returns the refined prompt as a string."
        "Input should be a string containing the original prompt, topic analysis JSON, and category breakdown JSON array."
        "Example input format: 'Prompt: [Original Prompt Here]\nTopic Analysis: [Topic Analysis JSON Here]\nCategory Breakdown: [Category Breakdown JSON Array Here]'"
    )
    # Add service and llm as attributes that will be passed during instantiation
    lmstudio_service: LMStudioService
    llm: Any # Or a more specific type if available

    def _run(self, tool_input: str) -> str:
        """
        Runs the iterative refinement logic by prompting LMStudio.
        This method is called by the CrewAI agent when the tool is used.
        Expects input in the format 'Prompt: ...\nTopic Analysis: ...\nCategory Breakdown: ...'.
        """
        logger.info(f"Executing Iterative Refinement Tool with input: {tool_input[:150]}...")

        # Parse the input string to extract prompt, topic analysis, and category breakdown
        # This is a simple parsing based on the expected input format
        prompt_content = ""
        topic_analysis_result_str = ""
        category_breakdown_result_str = ""
        lines = tool_input.split('\n')

        current_section = None
        for line in lines:
            if line.startswith("Prompt: "):
                prompt_content = line[len("Prompt: "):].strip()
                current_section = "Prompt"
            elif line.startswith("Topic Analysis: "):
                topic_analysis_result_str = line[len("Topic Analysis: "):].strip()
                current_section = "Topic Analysis"
            elif line.startswith("Category Breakdown: "):
                category_breakdown_result_str = line[len("Category Breakdown: "):].strip()
                current_section = "Category Breakdown"
            elif current_section == "Prompt":
                 prompt_content += "\n" + line.strip() # Append subsequent lines to prompt
            elif current_section == "Topic Analysis":
                 topic_analysis_result_str += "\n" + line.strip() # Append subsequent lines
            elif current_section == "Category Breakdown":
                 category_breakdown_result_str += "\n" + line.strip() # Append subsequent lines


        if not prompt_content:
             logger.error("Iterative Refinement Tool received input without 'Prompt:' prefix.")
             return json.dumps({"status": "error", "message": "Tool input missing original prompt."})

        # Construct prompt for LMStudio for refinement
        refinement_prompt = f"""
Refine and improve the following original prompt based on the provided analysis and breakdown.
Focus on clarity, specificity, structure, and effectiveness.

Original Prompt: {prompt_content}

Topic Analysis: {topic_analysis_result_str}

Category Breakdown: {category_breakdown_result_str}

Provide the refined prompt as your final output. Do not include any other text or formatting.
"""

        try:
            # Use the LMStudio service instance passed to the tool
            response = self.lmstudio_service.generate_completion(refinement_prompt)
            logger.info(f"Received response from LMStudio (first 50 chars): {response[:50]}...")

            # The expected output is just the refined prompt string
            # We don't need to parse JSON here, just return the response
            return response.strip() # Return the cleaned response string

        except Exception as e:
            logger.error(f"Error calling LMStudio service from Iterative Refinement tool: {e}")
            # Return an error message in a consistent format
            return f"Error during refinement: {e}" # Return error as a string

class IterativeRefinementAgent:
    """Agent responsible for iteratively refining the prompt"""

    def __init__(self, config: Dict[str, Any], lmstudio_service: LMStudioService, llm: Any):
        self.config = config
        self.lmstudio_service = lmstudio_service # Store the service instance
        self.llm = llm # Store llm

        # Instantiate the custom tool, passing necessary dependencies
        self.iterative_refinement_tool = IterativeRefinementTool(
            lmstudio_service=self.lmstudio_service,
            llm=self.llm # Pass the llm to the tool if needed within _run
        )

        # Initialize the CrewAI Agent here using the config
        self.agent = Agent(
            role=config.get("role", "Prompt Refinement Specialist"),
            goal=config.get("goal", "Refine and improve the user prompt based on analysis and context."),
            backstory=config.get("backstory", "A meticulous editor focused on clarity and effectiveness..."),
            verbose=config.get("verbose", False),
            allow_delegation=config.get("allow_delegation", False),
            max_iter=config.get("max_iter", 15),
            max_rpm=config.get("max_rpm", 100),
            llm=self.llm, # Pass the llm instance to the CrewAI Agent
            tools=[self.iterative_refinement_tool] # Assign the instantiated tool to the agent
        )
        self.last_result: Optional[IterativeRefinementResult] = None


