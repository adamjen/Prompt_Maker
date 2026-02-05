#!/bin/bash

# Simple startup script - just run the app directly
echo "Starting Prompt Maker..."

# Install dependencies with pip
echo "Installing dependencies..."
pip install -e .

# Run the application
echo "Starting application..."
uvicorn app.main:app --reload