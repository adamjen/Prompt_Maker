#!/bin/bash

# Direct startup script - install everything in the system Python
echo "Starting Prompt Maker directly with system Python..."

# Install uv globally
echo "Installing uv globally..."
python3 -m pip install uv

# Install dependencies with uv
echo "Installing dependencies with uv..."
uv pip install -r requirements.txt

# Run the application
echo "Starting application..."
uvicorn app.main:app --reload