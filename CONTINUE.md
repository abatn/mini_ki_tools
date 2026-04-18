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

15. **Workspace Configuration**
    - Module: `workspace.py`
    - Config: `config/workspace.yaml`
    - Description: Benutzerdefinierter Workspace-Pfad mit Lese-, Schreib- und Ausführungsrechten. Konfiguration über Umgebungsvariable `WORKSPACE_PATH` oder Konfigurationsdatei. Alle Tools (read_file, write_file, execute_code) arbeiten ausschließlich innerhalb des Workspace-Pfades. Features:
      - Pfad-Validierung gegen blocked_paths (/etc, /root, ~/.ssh, ~/.aws)
      - Nur-Lesen-Modus (read_only)
      - Maximale Dateigröße (10MB)
      - Execution Timeout (30s)
      - Automatischer Docker-Mount

16. **Fallback LLM Provider**
    - Module: `llm_provider.py`
    - Description: Automatischer Fallback zwischen LLM-Providern bei Ausfall. Reihenfolge: Ollama → OpenAI → Anthropic → OpenRouter. Konfiguration über Umgebungsvariablen:
      - `LLM_URL`: API-URL
      - `LLM_MODEL`: Modellname
      - `LLM_PROVIDER`: Provider-Typ
      - `LLM_API_KEY`: API-Schlüssel

## API Endpoints

### Health & Configuration
- `GET /health` - Health-Check mit Workspace- und LLM-Info
- `GET /workspace/config` - Workspace-Konfiguration abrufen
- `POST /workspace/config` - Workspace-Konfiguration aktualisieren

### Docker Usage
```bash
# Workspace mounten
docker run -d -p 8000:8000 \
  -v /host/path:/workspace \
  -e WORKSPACE_PATH=/workspace \
  -e LLM_URL="http://host:11434" \
  -e LLM_MODEL="llama3.2" \
  --name mini-ki-container mini-ki-tools
```

15. **VS Code Extension**
    - Verzeichnis: `vscode-extension/`
    - Beschreibung: VS Code Extension für direkte Integration mit dem Agent-Server
    - Features:
      - Chat-Panel für Kommunikation mit dem Agent
      - Status-Bar-Anzeige
      - Befehle: Mini KI Tools: Start, Chat, Apply Changes, Analyze, Refactor
      - Konfigurierbarer Server-URL (Standard: http://localhost:8000)
    - Build: `npm install && npm run compile` (erfolgreich)
    - Debug-Modus: Mit F5 starten

## Aktuelle Konfiguration (April 2026)

### Docker-Container
- Image: `mini-ki-tools`
- Port: 8000
- LLM_URL: `https://sheffield-narrative-freedom-moss.trycloudflare.com`
- LLM_MODEL: `qwen2.5-coder:1.5b`
- Volume: `~/mini_ki_tools/output:/app/output`

### TAO-Loop
- Generiert Code und Dateien
- Ausgabe landet im Host-Ordner `output/`

### VS Code Extension
- Kompiliert und bereit für Debug-Modus (F5)
- Verbindet sich mit `http://localhost:8000`

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

20. **LLM Provider Abstraction (Flexibel)**
   - Module: `llm_provider.py`
   - Config: `config/llm_config.yaml`
   - Description: Vollständig flexible LLM-Anbindung zur Laufzeit via Umgebungsvariablen konfigurierbar.
   - **Umgebungsvariablen**:
     - `LLM_URL`: Die Basis-URL der LLM API (z.B. http://localhost:11434, https://api.openai.com/v1)
     - `LLM_MODEL`: Das zu verwendende Modell (z.B. llama3.2, gpt-4, claude-3)
     - `LLM_PROVIDER`: Der Provider-Typ (ollama, openai, anthropic, openrouter)
     - `LLM_API_KEY`: API-Schlüssel für Cloud-Provider
   - **Unterstützte Provider**:
     - `OllamaProvider`: Lokale LLM-Verbindung (Standard: http://localhost:11434)
     - `OpenAIProvider`: API-basierte Verbindung (GPT-4, GPT-3.5)
     - `AnthropicProvider`: Claude API (Claude-3-Sonnet)
     - `OpenRouterProvider`: Aggregator für mehrere LLM-Anbieter
   - **Keine festen URLs oder Modelle im Code** - alles via Umgebungsvariablen konfigurierbar
   - **Kompatibel mit jeder OpenAI-ähnlichen API**

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

## Aktuelle Änderungen (April 2026)

### 1. Import-Struktur konsolidiert
- **Datum**: April 2026
- **Änderungen**:
  - `src/__init__.py` erweitert mit allen Public APIs für konsistente Importe
  - Relative Importe (`from .modul`) in 4 Dateien zu absoluten Importen konvertiert:
    - `tree_of_thoughts.py`
    - `agent_server.py`
    - `thought_action_observation.py`
    - `self_healing.py`
  - Optionale Dependencies mit Lazy Loading versehen:
    - `embedding.py` (sentence_transformers, torch)
    - `voice_interface.py` (faster_whisper, pyttsx3)
    - `long_term_memory.py` (chromadb)
    - `scheduler.py` (sqlalchemy)
  - Import-Fixes in `code_review.py` und `cli.py`
- **Docker**: Image gebaut mit `mini-ki-tools`, Container läuft mit LLM_URL und LLM_MODEL

### 2. Modell-Konfiguration zentralisiert
- **Datum**: April 2026
- **Problem**: TAOLoop hatte hartcodiertes "llama3.2" und ignorierte LLM_MODEL
- **Lösung**:
  - `thought_action_observation.py`: `model=None` als Default, liest aus `LLM_MODEL` env var
  - `llm_provider.py`: Neue Methoden `get_available_models()` und `get_default_model()`
  - Fallback-Logik: Wenn kein Modell gesetzt, wird erstes verfügbares Ollama-Modell verwendet
- **Kompatibel**: Mit CONTINUE.md (LLM Provider Abstraction)

### Docker-Setup
```bash
docker build -t mini-ki-tools .
docker run -d -p 8000:8000 \
  -e LLM_URL=http://host.docker.internal:11434 \
  -e LLM_MODEL=llama3.2 \
  --name mini-ki-container mini-ki-tools
```

### Bestätigungen
- ✅ IMPORT STRUKTUR KONSOLIDIERT
- ✅ MODELL KONFIGURATION ZENTRALISIERT
