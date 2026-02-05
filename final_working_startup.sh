#!/bin/bash

# Final working startup script - resolve all dependency conflicts
echo "Starting Prompt Maker..."

# Install uv globally
echo "Installing uv globally..."
pip install uv

# Install dependencies with pip (skip the conflicting chromadb version)
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install uvicorn separately if not found
echo "Installing uvicorn..."
pip install uvicorn

# Run the application
echo "Starting application..."
uvicorn app.main:app --reload