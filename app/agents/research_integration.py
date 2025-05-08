import logging
from crewai import Agent
from crewai.tools import BaseTool # Import BaseTool
# Assuming these models exist

from app.models.prompt import PromptRequest # Assuming PromptRequest might be needed for type hinting
from app.models.response import ResearchIntegrationResult # Import necessary result models
from app.services.lmstudio import LMStudioService # Import LMStudioService
from app.services.research import ResearchService # Import ResearchService
from typing import Dict, Any, List, Optional
from datetime import datetime
import json # Import json
from pydantic import BaseModel, Field # Import BaseModel and Field for Pydantic schema

logger = logging.getLogger(__name__)

# Define the Pydantic model for the actual input data fields for Research Integration
class ResearchIntegrationInputData(BaseModel):
    """Schema for the actual data fields within the Research Integration tool's input."""
    refined_prompt: str = Field(description="The refined prompt from the previous task.")
    original_prompt: str = Field(description="The original text prompt from the user.")
    additional_context: str = Field(description="Additional context or research findings as a JSON string.")

# Define the Pydantic model that CrewBase seems to expect for args_schema
# This model has a single field named 'tool_input'
class ResearchIntegrationToolInput(BaseModel):
    """Input schema for the ResearchIntegrationTool, structured to satisfy CrewBase validation."""
    # This 'tool_input' field is added to satisfy CrewBase's specific validation
    # The actual data the tool needs is nested within this field.
    tool_input: ResearchIntegrationInputData = Field(description="Container for the tool's input data.")


    def __init__(self, lmstudio_service: LMStudioService, llm: Any, research_service: ResearchService):
        self.lmstudio_service = lmstudio_service
        self.llm = llm
        self.research_service = research_service
        super().__init__()

    # The _run method now receives the validated ResearchIntegrationToolInput instance
    def _run(self, tool_input: 'ResearchIntegrationToolInput') -> str:
        """
        Runs the research integration logic.
        This method is called by the CrewAI agent when the tool is used.
        Receives input as a ResearchIntegrationToolInput instance with nested data.
        """
        logger.info(f"Executing Research Integration Tool...")
        input_data = tool_input.tool_input
        enhanced_prompt = self.research_service.integrate_research(
            input_data.refined_prompt,
            input_data.original_prompt,
            input_data.additional_context
        )
        return enhanced_prompt

class ResearchIntegrationTool(BaseTool):
    """Tool for integrating research findings into the prompt refinement process"""
    
    name: str = Field(default="Research Integration Tool", description="Name of the tool")
    description: str = Field(default="Integrates research findings into the prompt refinement", description="Description of the tool")
    lmstudio_service: LMStudioService = Field(..., description="LMStudio service instance")
    llm: Any = Field(..., description="LLM instance")
    research_service: ResearchService = Field(..., description="Research service instance")

    def __init__(self, lmstudio_service: LMStudioService, llm: Any, research_service: ResearchService):
        super().__init__(lmstudio_service=lmstudio_service, llm=llm, research_service=research_service)

    def _run(self, tool_input: ResearchIntegrationToolInput) -> str:
        # Implementation of the _run method
        logger.info(f"Executing Research Integration Tool...")
        input_data = tool_input.tool_input
        enhanced_prompt = self.research_service.integrate_research(
            input_data.refined_prompt,
            input_data.original_prompt,
            input_data.additional_context
        )
        return enhanced_prompt

class ResearchIntegrationAgent:
    """Agent responsible for integrating research findings into the prompt refinement"""

    def __init__(self, config: Dict[str, Any], lmstudio_service: LMStudioService, llm: Any, research_service: ResearchService):
        self.config = config
        self.lmstudio_service = lmstudio_service
        self.llm = llm
        self.research_service = research_service

        # Instantiate the custom tool, passing necessary dependencies
        self.research_integration_tool = ResearchIntegrationTool(
            lmstudio_service=self.lmstudio_service,
            llm=self.llm,
            research_service=self.research_service
        )

        # Initialize the CrewAI Agent here using the config
        self.agent = Agent(
            role=config.get("role", "Research Integration Specialist"),
            goal=config.get("goal", "Integrate relevant research findings to enrich the prompt."),
            backstory=config.get("backstory", "A diligent researcher who finds and synthesizes information..."),
            verbose=config.get("verbose", False),
            allow_delegation=config.get("allow_delegation", False),
            max_iter=config.get("max_iter", 15),
            max_rpm=config.get("max_rpm", 100),
            llm=self.llm,
            tools=[self.research_integration_tool]
        )
        self.last_result: Optional[ResearchIntegrationResult] = None

    # The process method is likely not needed if the task uses the tool directly.
    # Keeping it as a placeholder or for direct calls outside CrewAI flow if necessary.
    # Note: If you call this process method directly, you would need to construct
    # a ResearchIntegrationToolInput object with the nested structure.
    def process(self, inputs: ResearchIntegrationToolInput) -> ResearchIntegrationResult:
        """Process the input and integrate research (now handled by the tool)."""
        logger.warning("ResearchIntegrationAgent.process called directly. CrewAI task uses the ResearchIntegrationTool.")
        # Example: Call the tool's _run method if needed for direct processing
        tool_output_string = self.research_integration_tool._run(inputs) # Pass the inputs object
        # Assuming the tool returns the final prompt string directly
        result = ResearchIntegrationResult(
            status="success" if not tool_output_string.startswith("Error during final integration:") else "error",
            processing_time=0.0, # Placeholder
            integrated_output=tool_output_string if not tool_output_string.startswith("Error during final integration:") else "Error: " + tool_output_string,
            integration_details="Processed via direct tool call." if not tool_output_string.startswith("Error during final integration:") else tool_output_string,
            timestamp=datetime.now()
        )
        self.last_result = result
        return result
