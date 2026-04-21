# Mini KI Tools - Agent Guidance

## Quick Start

```bash
# Backend (required first)
pip install -r requirements.txt
python src/agent_server.py  # localhost:8000

# Frontend dev (optional, serves at / when built)
cd frontend && npm start  # localhost:3000
```

## Development Commands

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_<name>.py -v

# VS Code Extension
cd vscode-extension && npm run compile  # build
npm run bundle-python                  # bundle deps
```

## Docker

```bash
docker build -t mini-ki-tools .
docker run -p 8000:8000 -e LLM_URL=http://host.docker.internal:11434 mini-ki-tools
```

## Environment Variables

- `LLM_URL` - Ollama/OpenAI endpoint (default: http://localhost:11434)
- `LLM_MODEL` - Model name (default: llama3.2)
- `WORKSPACE_PATH` - Working directory for file operations
- `LLM_PROVIDER` - Provider type: ollama, openai, anthropic, openrouter
- Cloud providers require API keys via provider_manager (stored in config)

## Architecture

- **Entry point**: `src/agent_server.py` (FastAPI, serves frontend at `/` when built)
- **Core loop**: `src/thought_action_observation.py` (TAO-Loop)
- **Tools**: `src/tools.py` with permission checks in `src/agent_permissions.py`
- **VS Code**: `vscode-extension/extension.ts` ↔ `vscode-extension/python/src/extension_host.py`

## Key Conventions

1. **Python version**: 3.9+ (not 3.12)
2. **Build order**: `cd frontend && npm run build` before docker build for production
3. **Permissions**: Project-based `rules.json` in workspace root

   ```json
   {
     "tools": {
       "write_file": "allow",
       "execute_code": "ask",
       "run_command": "deny"
     },
     "task_budget": 10
   }
   ```

4. **VS Code settings**: Prefix `mini-ki-tools.`
   - `pythonPath`, `llmUrl`, `llmModel`, `workspacePath`

## Known Issues

- **Frontend 404**: Run `npm run build` in frontend/ first
- **Extension not connecting**: Check Python path in VS Code settings
- **LLM failed**: Verify Ollama running and model pulled

## Resources

- Config files: `config/workspace.yaml`, `config/llm_config.yaml`
- Tests: `tests/*.py`
- README: `README.md` (German), `CONTINUE.md` (detailed)