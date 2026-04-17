#!/bin/bash

# Setup script for Local Agent Tool

echo "Setting up Local Agent Tool..."

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs
mkdir -p data
mkdir -p src

echo "Setup complete!"
echo "Run 'python agent_server.py' to start the server"
echo "Or run 'docker build -t local-agent .' followed by 'docker run -p 8000:8000 local-agent'"