#!/bin/bash

# Working startup script - use system Python directly
echo "Starting Prompt Maker with system Python..."

# Install dependencies directly with pip
echo "Installing dependencies with pip..."
pip install -r requirements.txt

# Run the application
echo "Starting application..."
uvicorn app.main:app --reload