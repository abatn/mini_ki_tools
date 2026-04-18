# Mini KI Tools - VS Code Extension (Standalone Mode)

AI-powered coding assistant for VS Code - runs directly in VS Code without external container.

## Features

- 🤖 **Standalone Mode** - Agent runs directly in VS Code (no Docker/container required)
- 🔄 **Server Mode** - Fallback to external server if standalone not available
- 💬 **AI Chat** - Interactive chat with AI assistant in VS Code
- 📝 **Code Analysis** - Analyze current file with AI
- 🔄 **Refactoring** - Refactor selected code with AI assistance
- ✏️ **Inline Completions** - AI-powered code completions
- 📊 **Status Bar** - Shows connection status and mode
- 🔗 **VS Code API Integration** - Reads current file, cursor position, selection

## Requirements

- VS Code 1.75.0+
- Python 3.11+ (bundled with extension)
- LLM server (Ollama, OpenAI, or Anthropic)

## Environment Variables

- `LLM_URL`: LLM server URL (default: `http://localhost:11434`)
- `LLM_MODEL`: Model name (default: `llama3.2`)
- `LLM_PROVIDER`: Provider type (`ollama`, `openai`, `anthropic`)

## Installation

1. Navigate to the extension directory:
   ```bash
   cd vscode-extension
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Compile TypeScript:
   ```bash
   npm run compile
   ```

4. Press `F5` in VS Code to launch the extension

## Python Setup (First Time)

1. Run command "Mini KI Tools: Setup Python Environment"
2. Wait for Python bundling to complete
3. Restart VS Code

## Commands

| Command | Description |
|---------|-------------|
| `Mini KI Tools: Start Agent` | Start the agent (standalone or server) |
| `Mini KI Tools: Stop Agent` | Stop the standalone agent |
| `Mini KI Tools: Chat` | Open chat panel |
| `Mini KI Tools: Apply Changes` | Apply code changes from AI |
| `Mini KI Tools: Analyze Code` | Analyze current file |
| `Mini KI Tools: Refactor` | Refactor selected code |
| `Mini KI Tools: Inline Completion` | Get code completion |
| `Mini KI Tools: Setup Python Environment` | Setup bundled Python |

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `mini-ki-tools.pythonPath` | `${extensionPath}/python/venv/bin/python` | Bundled Python path |
| `mini-ki-tools.llmUrl` | `${env:LLM_URL}` | LLM server URL |
| `mini-ki-tools.llmModel` | `${env:LLM_MODEL}` | Model name |
| `mini-ki-tools.llmProvider` | `ollama` | Provider type |
| `mini-ki-tools.autoStart` | `false` | Auto-start on activation |
| `mini-ki-tools.workspacePath` | `${workspaceFolder}` | Workspace for agent files |

## Architecture

```
vscode-extension/
├── python/
│   ├── src/           # All 35 Python modules from mini_ki_tools
│   └── extension_host.py  # Bridge between VS Code and Python
├── src/
│   └── extension.ts   # VS Code extension (TypeScript)
├── package.json       # Extension manifest
└── bundle_python.sh   # Python bundling script
```

## Modules Included

The extension includes all core modules from mini_ki_tools:
- `agent.py`, `thought_action_observation.py`, `llm_provider.py`, `tools.py`
- `git_integration.py`, `long_term_memory.py`, `batch_processor.py`, `scheduler.py`
- `orchestrator.py`, `self_healing.py`, `subagents.py`, `mcp_client.py`
- `sandbox_manager.py`, `audit_logger.py`, `voice_interface.py`, `code_review.py`
- `code_refactoring_engine.py`, `tree_of_thoughts.py`, `config_exporter.py`
- `collaboration.py`, `plugin_manager.py`, `embedding.py`, `inline_completions.py`
- `security_scanner.py`, `undo_manager.py`, `utils.py`, `cli.py`, `workspace.py`

## Web UI (Separate)

The web-based UI remains available separately at `http://localhost:8000` for users without VS Code.

## WebView Features

- Chat interface with message history
- Shows current file info
- Connection status indicator
- Send messages via Enter or button

## Requirements

- VS Code 1.75.0+
- Mini KI Tools server running on configured URL

## Development

```bash
# Watch for changes
npm run watch

# Run tests
npm test
```

## License

MIT