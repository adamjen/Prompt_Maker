import os
import yaml
import logging
import json
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai.flow import Flow, start, listen # Import Flow, start, and listen
from typing import Dict, Any, List
from pathlib import Path
from pydantic import ValidationError

from app.services.lmstudio import LMStudioService, LMStudioLiteLLMWrapper

from app.agents.topic_analysis import TopicAnalysisAgent
from app.agents.category_breakdown import CategoryBreakdownAgent
from app.agents.iterative_refinement import IterativeRefinementAgent
from app.agents.research_integration import ResearchIntegrationAgent, ResearchIntegrationInputData, ResearchIntegrationToolInput

from app.models.prompt import PromptRequest

CONFIG_DIR = Path(__file__).parent / "config"
print(f"CONFIG_DIR: {CONFIG_DIR}")

logger = logging.getLogger(__name__)

# Define the Flow class
@CrewBase
class PromptEnhancerCrew:
    """CrewAI orchestration for the Prompt Enhancer System"""

    def __init__(self):
        # Initialize service and LLM instances
        self.lmstudio_service = LMStudioService()
        # Initialize LiteLLM wrapper
        self.litellm_llm = LMStudioLiteLLMWrapper(self.lmstudio_service)

        # Initialize custom agent wrappers
        agents_config = self._load_config("agents")
        self.topic_analysis_wrapper = TopicAnalysisAgent(agents_config.get("topic_analysis", {}), self.lmstudio_service, self.litellm_llm)
        self.category_breakdown_wrapper = CategoryBreakdownAgent(agents_config.get("category_breakdown", {}), self.lmstudio_service, self.litellm_llm)
        self.iterative_refinement_wrapper = IterativeRefinementAgent(agents_config.get("iterative_refinement", {}), self.lmstudio_service, self.litellm_llm)
        self.research_integration_wrapper = ResearchIntegrationAgent(agents_config.get("research_integration", {}), self.lmstudio_service, self.litellm_llm)

    def _load_config(self, config_name: str) -> Dict[str, Any]:
        """Helper to load a specific configuration file"""
        config_path = CONFIG_DIR / f"{config_name}.yaml"
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file {config_path}: {e}")
            raise

    @agent
    def topic_analysis_agent(self) -> Agent:
        """Returns the CrewAI Topic Analysis Agent instance."""
        return self.topic_analysis_wrapper.agent

    @agent
    def category_breakdown_agent(self) -> Agent:
        """Returns the CrewAI Category Breakdown Agent instance."""
        return self.category_breakdown_wrapper.agent

    @agent
    def iterative_refinement_agent(self) -> Agent:
        """Returns the CrewAI Iterative Refinement Agent instance."""
        return self.iterative_refinement_wrapper.agent

    @agent
    def research_integration_agent(self) -> Agent:
        """Returns the CrewAI Research Integration Agent instance."""
        return self.research_integration_wrapper.agent

    @task
    def topic_analysis_task(self) -> Task:
        """Creates and returns the Topic Analysis Task"""
        tasks_config = self._load_config("tasks")
        task_config = tasks_config.get("topic_analysis_task", {})
        return Task(
            description=task_config.get("description", "Default topic analysis description."),
            expected_output=task_config.get("expected_output", "A JSON object containing core topics, domain, complexity, and key entities."),
            agent=self.topic_analysis_agent(),
            tools=[self.topic_analysis_wrapper.topic_analysis_tool],
        )

    @task
    def category_breakdown_task(self) -> Task:
        """Creates and returns the Category Breakdown Task"""
        tasks_config = self._load_config("tasks")
        task_config = tasks_config.get("category_breakdown_task", {})
        return Task(
            description=task_config.get("description", "Default category breakdown description."),
            expected_output=task_config.get("expected_output", "A list of strings, where each string is a identified category or sub-topic."),
            agent=self.category_breakdown_agent(),
            # tools=[self.category_breakdown_wrapper.category_breakdown_tool], # Add tool if exists
        )

    @task
    def iterative_refinement_task(self) -> Task:
        """Creates and returns the Iterative Refinement Task"""
        tasks_config = self._load_config("tasks")
        task_config = tasks_config.get("iterative_refinement_task", {})
        return Task(
            description=task_config.get("description", "Default iterative refinement description."),
            expected_output=task_config.get("expected_output", "A significantly improved and more detailed version of the original prompt."),
            agent=self.iterative_refinement_agent(),
            # tools=[self.iterative_refinement_wrapper.iterative_refinement_tool], # Add tool if exists
        )

    @task
    def research_integration_task(self) -> Task:
        """Creates and returns the Research Integration Task"""
        tasks_config = self._load_config("tasks")
        task_config = tasks_config.get("research_integration_task", {})
        return Task(
            description=task_config.get("description", "Default research integration description."),
            expected_output=task_config.get("expected_output", "The refined prompt with relevant research findings integrated."),
            agent=self.research_integration_agent(),
            tools=[self.research_integration_wrapper.research_integration_tool], # Add tool if exists
        )

    @crew
    def get_crew(self) -> Crew:
        """Creates and returns the Prompt Enhancer crew"""
        return Crew(
            agents=[
                self.topic_analysis_agent(),
                self.category_breakdown_agent(),
                self.iterative_refinement_agent(),
                self.research_integration_agent(),
            ],
            tasks=[
                self.topic_analysis_task(),
                self.category_breakdown_task(),
                self.iterative_refinement_task(),
                self.research_integration_task(),
            ],
            process=Process.sequential,
            verbose=True,
        )
