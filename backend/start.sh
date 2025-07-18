#!/bin/bash

# SignalOS Backend Startup Script

echo "🚀 Starting SignalOS Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs
mkdir -p models

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please configure .env with your settings"
fi

# Start the backend
echo "Starting SignalOS Backend on http://0.0.0.0:8000"
echo "API Documentation: http://0.0.0.0:8000/api/docs"
echo ""

python main.py