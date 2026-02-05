#!/bin/bash

# Final startup script - clean approach
echo "Starting Prompt Maker..."

# Remove existing virtual environment if it exists
rm -rf .venv

# Create new virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install uv
echo "Installing uv..."
pip install uv

# Install dependencies with uv
echo "Installing dependencies with uv..."
uv pip install -r requirements.txt

# Run the application
echo "Starting application..."
uvicorn app.main:app --reload