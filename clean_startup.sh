#!/bin/bash

# Clean startup script - properly install and run the application
echo "Starting Prompt Maker..."

# Check if virtual environment exists, if not create it
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install all dependencies from requirements.txt
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Install uvicorn if not already installed
echo "Installing uvicorn..."
pip install uvicorn

# Run the application
echo "Starting application..."
uvicorn app.main:app --reload