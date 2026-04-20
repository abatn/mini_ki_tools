# Mini KI Tools - Agent Guidance

## Essential Commands

**Start Development**
- Frontend dev server: `cd frontend && npm start` (localhost:3000)
- Backend server: `python src/agent_server.py` (localhost:8000)
- VS Code Extension: `cd vscode-extension && npm run compile` then F5 to debug

**Testing**
- Run all tests: `python -m pytest tests/`
- Run specific test: `python -m pytest tests/test_<name>.py -v`

**VS Code Extension**
- Compile: `cd vscode-extension && npm run compile`
- Bundle Python deps: `cd vscode-extension && npm run bundle-python`
- Python venv setup: `cd vscode-extension/python && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

**Docker**
- Build: `docker build -t mini-ki-tools .`
- Run: `docker run -p 8000:8000 -e LLM_URL=http://host.docker.internal:11434 mini-ki-tools`
- With workspace mount: `docker run -p 8000:8000 -v $(pwd):/workspace -e WORKSPACE_PATH=/workspace -e LLM_URL=http://host.docker.internal:11434 mini-ki-tools`

## Architecture Overview

**Main Components**
1. **Web UI** (`frontend/`) - React app served at localhost:3000 (dev) or served by backend at `/`
2. **VS Code Extension** (`vscode-extension/`) - TypeScript extension communicating via stdin/stdout with Python host
3. **Python Backend** (`src/`) - FastAPI server implementing TAO-Loop agent with 50+ API endpoints
4. **Shared Python** (`python/`) - Virtual environment for LLM integration used by extension

**Key Files**
- Entry point: `src/agent_server.py` (FastAPI application with CORS, static file serving, WebSocket support)
- Extension communication: `vscode-extension/extension.ts` ↔ `vscode-extension/python/src/extension_host.py`
- Frontend served from: `frontend/build/` (built by backend at root `/`)

## UI & Navigation
- **Sidebar with Icons** for 6 main functions: Chat, Analyze, Refactor, Completion, Agent, Settings
- **Dropdown menu** for language selection (English, Arabic, French)
- **Unified dashboard** – all functions in one extension, no separate commands needed
- RTL support for Arabic UI with Cairo font, GitHub Dark+/VSCode Dark+ theme

## Automatic Setup (Zero-Configuration)
- The extension creates on first start automatically:
  - Virtual environment (`python/venv/`)
  - Installs dependencies (`pip install -r requirements.txt`)
  - Starts `extension_host.py` as a subprocess
- **User only needs to configure LLM URL, model, token limits, and permissions**

## Permissions & Rules System
- Project-based `rules.json` in workspace:
  ```json
  {
    "tools": {
      "write_file": "allow",
      "execute_code": "ask",
      "run_command": "deny"
    },
    "directories": ["/workspace/src", "/workspace/tests"],
    "max_file_size_mb": 10
  }
  ```
- Permissions checked via `agent_permissions.py` with tool-pattern rules (ALLOW/DENY/ASK)
- Task budgets per agent to prevent infinite loops

## Important Conventions

**Environment Variables** (check .env or process.env)
- `LLM_URL`: Ollama/OpenAI/etc endpoint (default: http://localhost:11434)
- `LLM_MODEL`: Model name (default: llama3.2)
- `WORKSPACE_PATH`: Working directory for file operations (defaults to current directory)
- `LLM_PROVIDER`: Provider type (ollama, openai, anthropic, openrouter)

**VS Code Extension Specifics**
- Settings stored in VS Code settings.json with prefix "mini-ki-tools."
- Key settings: `mini-ki-tools.pythonPath`, `mini-ki-tools.llmUrl`, `mini-ki-tools.llmModel`, `mini-ki-tools.workspacePath`
- Commands registered in package.json under contributes.commands (Start, Stop, Chat, Apply Changes, Analyze, Refactor, etc.)

**Workflow Notes**
1. Build frontend first for production: `cd frontend && npm run build`
2. Backend serves built frontend at root `/` when available
3. Extension requires Python environment setup (see bundle-python script)
4. Tests may require internet access for LLM provider validation
5. Git integration tests need configured git user

**Troubleshooting**
- Frontend not showing: Ensure `frontend/build/index.html` exists (run build)
- LLM connection failed: Verify Ollama running (`ollama list`) and model pulled (`ollama pull llama3.2`)
- Extension not connecting: Check Python path in VS Code settings and that extension host is running
- Port conflicts: Backend defaults to 8000, frontend dev server to 3000