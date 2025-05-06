import dotenv
import os
import logging

logger = logging.getLogger(__name__)

def load_environment_variables():
    """Loads environment variables from a .env file."""
    dotenv.load_dotenv()
    logger.info("Environment variables loaded.")

# Call the function immediately when the module is imported
load_environment_variables()