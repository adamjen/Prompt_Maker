import os
import argparse
import logging
import uvicorn
from pathlib import Path
import requests
import subprocess
import sys # Import sys

# Load environment variables early
import app.config.env_config
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("prompt_enhancer.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("prompt_enhancer")

def check_lmstudio_running():
    """Check if LMStudio is running and accessible"""
    try:
        response = requests.get("http://localhost:1234/v1/models")
        if response.status_code == 200:
            logger.info("LMStudio is running")
            return True
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to LMStudio. Please ensure it is running.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while checking LMStudio: {e}")

    logger.error("LMStudio is not running or accessible.")
    return False

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description="AI-Driven Prompt Enhancer")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")

    # Check if the script is being run directly or imported (like by pytest)
    # If run directly, parse sys.argv; otherwise, parse an empty list
    if __name__ == "__main__":
        args = parser.parse_args()
    else:
        # When imported (e.g., by pytest), parse an empty list to avoid SystemExit
        args = parser.parse_args([])


    # Check if LMStudio is running
    if not check_lmstudio_running():
        logger.info("LMStudio is not running. Attempting to start it...")
        try:
            # Use shell=True with caution or provide full path to 'lms'
            # It's generally safer to provide the full command as a list
            # Ensure 'lms' is in your system's PATH or provide its full path
            process = subprocess.Popen(["lms", "server", "start"])
            logger.info(f"LMStudio server start command executed. Process ID: {process.pid}")
            # Note: Popen starts the process and returns immediately.
            # It doesn't wait for the server to be fully ready.
            # You might need a short delay or a loop to check if it's ready.
        except FileNotFoundError:
             logger.error("Error: 'lms' command not found. Please ensure LMStudio is installed and in your system's PATH.")
             return
        except Exception as e:
            logger.error(f"Failed to start LMStudio automatically: {e}")
            return

    # Run FastAPI
    logger.info(f"Starting FastAPI server on {args.host}:{args.port}")
    # Assuming app.main:app is the correct entry point for uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.debug
    )

if __name__ == "__main__":
    # Ensure this block is only executed when the script is run directly
    main()
