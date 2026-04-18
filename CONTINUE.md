# CONTINUE Project Guide

## Project Overview
This project is a Python-based application with various modules for different functionalities. It follows a structured organization with distinct directories for configuration, frontend, plugins, source code.

## Getting Started
### Prerequisites
- Python 3.12 or higher
- Virtual environment (`venv`)

### Installation Instructions
1. Clone the repository.
2. Navigate to the project directory.
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:
   ```bash
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
5. Install dependencies using pip:
   ```bash
   pip install -r requirements.txt
   ```

### Basic Usage Examples
To start the agent server, execute:
```bash
python src/agent_server.py
```

## Project Structure
### Main Directories and Their Purpose
- **src/**: Main source code directory containing various modules.
- **frontend/**: Frontend code (if applicable).
- **config/**: Configuration files.
- **plugins/**: Plugin modules.

### Key Files and Their Roles
- `requirements.txt`: Dependency management file.
- `setup.sh`: Setup script for the project.
- `src/agent_server.py`: Main agent server module.

## Implemented Features
1. **Long-Term Memory**
   - Module: `long_term_memory.py`
   - Description: Manages long-term memory storage and retrieval.

2. **Git Integration**
   - Module: `git_integration.py`
   - Description: Provides integration with Git for version control operations.

3. **Debugger**
   - Module: `debugger.py`
   - Description: Offers debugging tools to help identify and fix issues in the code.

4. **Voice Interface**
   - Module: `voice_interface.py`
   - Description: Enables voice-based interaction with the system.

5. **Batch Processor**
   - Module: `batch_processor.py`
   - Description: Processes tasks in batch mode for efficiency.

6. **Scheduler**
   - Module: `scheduler.py`
   - Description: Manages scheduled tasks and events.

7. **Plugin Manager**
   - Module: `plugin_manager.py`
   - Description: Handles the loading, unloading, and management of plugins.

8. **Code Review**
   - Module: `code_review.py`
   - Description: Provides tools for code review and analysis.

9. **MCP Server**
   - Module: `mcp_server.py`
   - Description: Manages the MCP server for communication and control.

10. **Tree of Thoughts**
    - Module: `tree_of_thoughts.py`
    - Description: Autonomous Task Planning - Agent plant kompletten Baum von Aktionen, bewertet Pfade, wählt optimalen. Integration in agent.py.

11. **Code Refactoring Engine**
    - Module: `code_refactoring_engine.py`
    - Description: Provides tools for automated code refactoring.

12. **Collaboration Mode**
    - Module: `collaboration.py`
    - Description: WebSocket-based multi-user collaboration with UUID rooms, broadcast messaging, and commands: /collab create, /collab join, /collab leave.

13. **Config Exporter/Importer**
    - Module: `config_exporter.py`
    - Description: Export/import complete agent configuration as .agentconfig (YAML) with models, tools, MCP-servers, plugins. Commands: /export, /import.

14. **Sandboxing (Docker Isolation)**
    - Module: `sandbox_manager.py`
    - Description: Jede Tool-Ausführung in eigenem Docker-Container mit Zeitlimit 5min, CPU/RAM-Limits, read-only System.

15. **Audit Log (Compliance)**
    - Module: `audit_logger.py`
    - Description: Jede Aktion protokollieren (user_id, timestamp, action_type, file, prompt, result). Verschlüsselung mit Fernet. Admin-Befehle: /audit export, /audit search.

16. **VS Code Extension**
    - Directory: `vscode-extension/`
    - Description: Extension öffnet WebView mit Agent-UI, unterstützt automatisches Apply von Code-Änderungen (Diff-Editor), liest aktuelle Datei/Cursor-Position via VS Code API.

17. **Inline Autovervollständigung (Tab Completions)**
    - Module: `inline_completions.py`
    - Description: Generiert Vorschläge via lokales LLM (Ollama) für Code-Vervollständigung basierend auf aktueller Cursor-Position und Kontext.

18. **Orchestrator Mode (Multi-Agent)**
    - Module: `orchestrator.py`
    - Description: Komplexe Tasks werden in Subtasks zerlegt (Architect → Code → Debug → Test). Jeder Sub-Agent hat spezialisierte Tools und Prompt-Template.

19. **Self-Healing via Test Suites**
    - Module: `self_healing.py`
    - Description: Nach Code-Änderung führt Agent automatisch pytest aus. Bei Fehlern analysiert LLM den Traceback, generiert Fix, wendet an (max 3 Iterationen).

20. **LLM Provider Abstraction**
   - Module: `llm_provider.py`
   - Config: `config/llm_config.yaml`
   - Description: Zentrale Abstraktionsschicht für verschiedene LLM-Anbieter mit einheitlicher `generate()` Methode.
   - **Unterstützte Provider**:
     - `OllamaProvider`: Lokale LLM-Verbindung (http://localhost:11434)
     - `OpenAIProvider`: API-basierte Verbindung (GPT-4, GPT-3.5)
     - `AnthropicProvider`: Claude API (Claude-3-Sonnet)
     - `OpenRouterProvider`: Aggregator für mehrere LLM-Anbieter
   - **Methoden**:
     - `generate(prompt, system_prompt, **kwargs)`: Einheitliche Generate-Methode
     - `is_available()`: Prüft Verfügbarkeit des Providers
     - `get_name()`: Gibt Providernamen zurück
     - `get_default_model()`: Gibt Standard-Modell zurück
   - **Zentrale Verwaltung**:
     - `LLMProviderManager`: Zentrale Verwaltung der Provider
     - `get_llm_manager()`: Globale Instanz für einfachen Zugriff
     - `switch_provider(name)`: Wechsle zu anderem Provider zur Laufzeit

21. **MCP Marketplace**
    - Module: `mcp_marketplace.py`
    - Config: `config/mcp_marketplace.json`
    - Description: Registry mit öffentlichen MCP-Servern (GitHub, Slack, Database). Befehl: /mcp search, /mcp install <name>, /mcp update.

21. **CLI / Headless Mode**
    - Module: `cli.py`
    - Description: Agent läuft ohne Web-UI, gibt Ergebnisse als JSON/Text aus. Perfekt für CI/CD Pipelines. Unterstützt --headless, --task, --output json.

22. **Native Subagents (Parallel)**
    - Module: `subagents.py`
    - Description: Subagents laufen parallel via asyncio.gather. Jeder Subagent hat eigene Tools, LLM-Client, Memory. Hauptagent aggregiert Ergebnisse.

## API Endpoints
- `/api/`: Base endpoint.
  - `/chat`: Endpoint to process chat messages.
  - `/tools`: Endpoint to get list of available tools.
  - `/health`: Health check endpoint.
  - `/git/commit`: Commit changes to git repository.
  - `/git/branch`: Create or switch to a branch.
  - `/memory/store`: Store a memory in the vector database.
  - `/memory/search`: Search memories in the vector database.
  - `/batch/process_files_parallel`: Process files in parallel.
  - `/schedule/add`: Add a scheduled job.
  - `/schedule/list`: List all scheduled jobs.
  - `/schedule/remove`: Remove a scheduled job.
  - `/ws/collab`: WebSocket endpoint for real-time collaboration.
  - `/api/collab/rooms`: List all active collaboration rooms.
  - `/api/config/export`: Export configuration to .agentconfig file.
  - `/api/config/import`: Import configuration from .agentconfig file.
  - `/api/sandbox/execute`: Execute command in isolated sandbox.
  - `/api/sandbox/active`: List active sandboxes.
  - `/api/sandbox/{sandbox_id}`: Kill a sandbox.
  - `/api/audit/log`: Log an action to audit.
  - `/api/audit/search`: Search audit logs.
  - `/api/audit/export`: Export audit logs.
  - `/api/audit/stats`: Get audit statistics.
  - `/api/orchestrator/execute`: Execute task with multi-agent orchestrator.
  - `/api/orchestrator/status`: Get current orchestrator status.
  - `/api/orchestrator/roles`: Get available agent roles.
  - `/api/orchestrator/reset`: Reset orchestrator state.
  - `/api/self-healing/run`: Run self-healing process.
  - `/api/self-healing/status`: Get self-healing status.
  - `/api/mcp/marketplace/servers`: List available MCP servers.
  - `/api/mcp/marketplace/search`: Search MCP servers.
  - `/api/mcp/marketplace/install/{name}`: Install MCP server.
  - `/api/mcp/marketplace/uninstall/{name}`: Uninstall MCP server.
  - `/api/mcp/marketplace/update`: Update MCP server(s).
  - `/api/mcp/marketplace/config/{name}`: Get MCP server configuration.
  - `/api/mcp/marketplace/categories`: Get all categories.
  - `/api/subagents/execute`: Execute task with subagents.
  - `/api/subagents/status`: Get subagent status.
  - `/api/subagents/aggregate`: Aggregate subagent results.
  - `/api/llm/providers`: Liste alle verfügbaren LLM Provider mit Status.
  - `/api/llm/switch`: Wechsle zu einem anderen LLM Provider.

## Comparison with Cline/Kilo Feature Set
- **Implemented Features**: Long-Term Memory, Git Integration, Debugger, Voice Interface, Batch Processor, Scheduler, Plugin Manager, Code Review, MCP Server, Tree of Thoughts (Autonomous Planning), Code Refactoring Engine, Collaboration Mode, Config Export/Import, Sandboxing (Docker), Audit Log (Compliance).
- **Missing Features** (compared to Cline/Kilo):
  - SSH
  - Rate Limiting
  - Checkpoints

## TODO List
1. ~~Implement Collaboration features.~~ (FERTIG - Teil 24)
2. ~~Implement Config Export/Import.~~ (FERTIG - Teil 25)
3. ~~Implement Autonomous Task Planning (Tree of Thoughts).~~ (FERTIG - Teil 31)
4. ~~Implement Sandboxing (Docker Isolation).~~ (FERTIG - Teil 26)
5. ~~Implement Audit Log (Compliance).~~ (FERTIG - Teil 28)
6. ~~Implement VS Code Extension.~~ (FERTIG - Teil 33)
7. ~~Implement Inline Autovervollständigung.~~ (FERTIG - Teil 34)
8. ~~Implement Orchestrator Mode.~~ (FERTIG - Teil 35)
9. ~~Implement Self-Healing via Test Suites.~~ (FERTIG - Teil 37)
10. ~~Implement MCP Marketplace.~~ (FERTIG - Teil 38)
11. ~~Implement LLM Provider Abstraction.~~ (FERTIG - Teil 20)
12. Integrate SSH capabilities.
13. Set up Rate Limiting.
14. Create Checkpoint functionality.

## Troubleshooting
### Common Issues and Their Solutions
- **Missing Dependencies**:
  - Ensure all dependencies in `requirements.txt` are installed.
- **API Endpoint Errors**:
  - Verify that the agent server is running and check for any configuration issues.

### Debugging Tips
- Use logging (e.g., Python's built-in `logging` module) to debug issues.
- Utilize breakpoints and debugging tools like `pdb`.

## References
### Links to Relevant Documentation
- [Python Documentation](https://docs.python.org/3/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Important Resources
- The `README.md` file for general information.
- The `.github/workflows` directory for CI/CD pipeline configurations.

---
Please review and edit the `CONTINUE.md` file as needed, commit it to your repository to share with your team, and inform them that Continue will automatically load this file into context when working with the project. Additionally, you can create additional `rules.md` files in subdirectories for more specific documentation related to those components.
```

### Final Steps

1. **Review and Edit the File**: Please open the newly updated `CONTINUE.md` file, review its contents, and make any necessary edits to ensure it accurately reflects your project's structure and conventions.

2. **Commit the File**: Once you're satisfied with the content, commit the `CONTINUE.md` file to your repository:
   ```bash
   git add CONTINUE.md
   git commit -m "Update CONTINUE.md with implemented features and TODO list"
   git push origin main
   
## Implemented Features
1. **Long-Term Memory**
   - Module: `long_term_memory.py`
   - Description: Manages long-term memory storage and retrieval.

2. **Git Integration**
   - Module: `git_integration.py`
   - Description:
     - Commit changes to git repository.
     - Create or switch to a branch.
     - Merge branches.
     - View diff between commits.
     - Blame lines of code to find authors.
     - Revert changes in the repository.
     - Cherry-pick specific commits.

3. **Debugger**
   - Module: `debugger.py`
   - Description: Offers debugging tools to help identify and fix issues in the code.

4. **Voice Interface**
   - Module: `voice_interface.py`
   - Description: Enables voice-based interaction with the system.

5. **Batch Processor**
   - Module: `batch_processor.py`
   - Description: Processes tasks in batch mode for efficiency.

6. **Scheduler**
   - Module: `scheduler.py`
   - Description: Manages scheduled tasks and events.

7. **Plugin Manager**
   - Module: `plugin_manager.py`
   - Description: Handles the loading, unloading, and management of plugins.

8. **Code Review**
   - Module: `code_review.py`
   - Description: Provides tools for code review and analysis.

9. **MCP Server**
   - Module: `mcp_server.py`
   - Description: Manages the MCP server for communication and control.

10. **Tree of Thoughts**
    - Module: `tree_of_thoughts.py`
    - Description: Implements a tree-of-thoughts approach for problem-solving.
   - Status: 🟢 IMPLEMENTIERT

11. **Code Refactoring Engine**
    - Module: `code_refactoring_engine.py`
    - Description: Provides tools for automated code refactoring.
   - Status: 🟢 IMPLEMENTIERT
