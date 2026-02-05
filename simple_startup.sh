#!/bin/bash

# Simple startup script using uv directly
echo "Starting Prompt Maker with uv..."

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    python3 -m pip install uv
fi

# Install dependencies with uv
echo "Installing dependencies with uv..."
uv pip install -r requirements.txt

# Run the application
echo "Starting application..."
uvicorn app.main:app --reload