#!/bin/bash

echo "Starting Raiden AI deployment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Set environment variables (you'll need to set your actual API key)
echo "Setting up environment..."
export GROQ_API_KEY="your_api_key_here"
export FLASK_ENV="development"

# Initialize database
echo "Initializing database..."
python3 -c "from server import init_db; init_db()"

# Start the application
echo "Starting Raiden AI..."
echo "Access the application at: http://localhost:5000"
python3 server.py 