#!/bin/bash
# Activate the virtual environment
source .venv/bin/activate

# Install dependencies using uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    pip install uv
fi

# Install dependencies using uv
echo "Installing dependencies with uv..."
uv pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload
