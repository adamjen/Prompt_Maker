import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime # <-- Add this import
import json
from crewai import Task # Import Task

# Assuming these models and agent classes exist
from app.models.prompt import PromptRequest
from app.models.response import TopicAnalysisResult # Assuming you have a result model for Topic Analysis
from app.agents.topic_analysis import TopicAnalysisAgent, TopicAnalysisTool, TopicAnalysisToolInput, TopicAnalysisInputData # Import TopicAnalysisTool and its input models
# Import other agent test classes if they are in this file
from app.services.lmstudio import LMStudioService # Import LMStudioService

class TestTopicAnalysisAgent(unittest.TestCase):
    def setUp(self):
        # Instantiate the actual LMStudioService
        # Note: This assumes LMStudioService can be instantiated without a running LMStudio server for testing purposes,
        # or that the test environment handles this (e.g., by mocking os.getenv or the underlying requests calls).
        # If LMStudioService.__init__ makes blocking calls, it might need further mocking.
        self.lmstudio_service = LMStudioService()

        # Mock the generate_completion method of the actual LMStudioService instance
        # This allows controlling the LLM response during the test
        self.patcher = patch.object(self.lmstudio_service, 'generate_completion')
        self.mock_generate_completion = self.patcher.start()

        # Mock the LLM object (still needed for the Agent constructor and tool)
        self.mock_llm = MagicMock()

        # Provide a dummy config dictionary
        agent_config = {
            "role": "Topic Analyzer",
            "goal": "Identify core topics, domain, complexity, and key entities from a user prompt.",
            "backstory": "An expert in natural language processing...",
            "verbose": False,
            "allow_delegation": False,
            "max_iter": 15,
            "max_rpm": 100
        }

        # Initialize the TopicAnalysisAgent with the actual service instance, config, and mock llm
        # This agent instance contains the CrewAI Agent object and the TopicAnalysisTool instance
        self.topic_analysis_agent_instance = TopicAnalysisAgent(agent_config, self.lmstudio_service, self.mock_llm)

    def tearDown(self):
        # Stop the patcher to clean up the mock after each test
        self.patcher.stop()

    def test_tool_run_valid_prompt(self):
        """Tests the agent's tool's _run method directly with a valid prompt."""
        # Mock a valid JSON response from LMStudio that the tool's _run method is expected to return
        mock_tool_output_data = {
            "core_topics": ["transformer models", "NLP", "applications"],
            "domain": "Technology",
            "complexity": "high", # Using string complexity as per updated tool
            "key_entities": ["transformer models", "NLP"]
        }
        # The mock generate_completion should return the JSON string that the tool's _run method would parse and return
        self.mock_generate_completion.return_value = json.dumps(mock_tool_output_data)

        # Create structured input for the tool's _run method
        tool_input_data = TopicAnalysisToolInput(tool_input=TopicAnalysisInputData(text_to_analyze="Explain how transformer models work in NLP and their applications."))

        # Call the tool's _run method with the structured input
        tool_output_json_string = self.topic_analysis_agent_instance.topic_analysis_tool._run(tool_input_data)

        # Parse the JSON output string from the tool
        try:
            parsed_output = json.loads(tool_output_json_string)
        except json.JSONDecodeError:
            self.fail(f"Tool output is not valid JSON: {tool_output_json_string}")

        # Assertions on the parsed output
        self.assertIsInstance(parsed_output, dict)
        self.assertIsNone(parsed_output.get("status"), "Status should not be present for a valid response")
        self.assertEqual(parsed_output.get("core_topics"), ["transformer models", "NLP", "applications"])
        self.assertEqual(parsed_output.get("domain"), "Technology")
        self.assertEqual(parsed_output.get("complexity"), "high")
        self.assertEqual(parsed_output.get("key_entities"), ["transformer models", "NLP"])

        # Verify LMStudio service's generate_completion was called correctly by the tool
        self.mock_generate_completion.assert_called_once()
        # You might want to assert the arguments passed to mock_generate_completion

    def test_tool_run_invalid_response(self):
        """Tests the agent's tool's _run method directly with an invalid LMStudio response."""
        # Mock an invalid JSON response from LMStudio
        self.mock_generate_completion.return_value = "Invalid JSON"

        # Create structured input for the tool's _run method
        tool_input_data = TopicAnalysisToolInput(tool_input=TopicAnalysisInputData(text_to_analyze="Test prompt"))

        # Call the tool's _run method
        tool_output_json_string = self.topic_analysis_agent_instance.topic_analysis_tool._run(tool_input_data)

        # Parse the JSON output string from the tool
        try:
            parsed_output = json.loads(tool_output_json_string)
        except json.JSONDecodeError:
            self.fail(f"Tool output is not valid JSON: {tool_output_json_string}")

        # Assertions for error handling
        self.assertIsInstance(parsed_output, dict)
        self.assertEqual(parsed_output.get("status"), "error")
        self.assertIn("Tool received response without valid JSON object structure", parsed_output.get("message", "")) # Correct assertion for invalid JSON structure
        self.assertIsNotNone(parsed_output.get("raw_response")) # Ensure raw response is included

        # Verify LMStudio service was called correctly by the tool
        self.mock_generate_completion.assert_called_once()

# Add other agent test classes here if they are in the same file
# class TestCategoryBreakdownAgent(unittest.TestCase):
#     ...

# Add the main block to run the tests
if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False) # Use argv and exit=False for running in environments like VS Code test runner

# Note: The original test_env_loading.py content was moved to a separate file and is not part of this agent test file.
