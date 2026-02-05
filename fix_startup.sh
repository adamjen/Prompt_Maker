#!/bin/bash
# Fixed startup script with better error handling

echo "Creating fresh virtual environment..."
rm -rf .venv
python3 -m venv .venv

if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment"
    exit 1
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing uv..."
pip install uv

if [ $? -ne 0 ]; then
    echo "Error: Failed to install uv"
    exit 1
fi

echo "Installing dependencies with uv..."
uv pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

echo "Starting the application..."
uvicorn app.main:app --reload

echo "Application started successfully!"