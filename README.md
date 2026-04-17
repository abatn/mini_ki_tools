# Local Agent Tool

A local AI agent with web UI that can read/write files, execute code, make HTTP requests, and run terminal commands using local LLMs (Ollama).

## Features
- Web UI with React frontend
- Local LLM support (Ollama)
- File operations (read/write)
- Code execution (Python)
- HTTP requests
- Terminal commands
- Agent loop with Thought → Action → Observation
- Docker support

## Setup
```bash
# Install dependencies
./setup.sh

# Run with Docker
docker build -t local-agent .
docker run -p 8000:8000 local-agent

# Or run directly
pip install -r requirements.txt
python agent_server.py
```

## Usage
1. Start the server
2. Open http://localhost:8000
3. Type prompts like ">> hilf mir, CSV zu laden"
4. Agent will execute actions automatically