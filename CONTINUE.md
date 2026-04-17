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
    - Description: Implements a tree-of-thoughts approach for problem-solving.

11. **Code Refactoring Engine**
    - Module: `code_refactoring_engine.py`
    - Description: Provides tools for automated code refactoring.

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

## Comparison with Cline/Kilo Feature Set
- **Implemented Features**: Long-Term Memory, Git Integration, Debugger, Voice Interface, Batch Processor, Scheduler, Plugin Manager, Code Review, MCP Server, Tree of Thoughts, Code Refactoring Engine.
- **Missing Features** (compared to Cline/Kilo):
  - Collaboration
  - Sandboxing
  - Audit Log
  - SSH
  - Rate Limiting
  - Checkpoints

## TODO List
1. Implement Collaboration features.
2. Add Sandboxing environment.
3. Develop an Audit Log system.
4. Integrate SSH capabilities.
5. Set up Rate Limiting.
6. Create Checkpoint functionality.

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
    - Status: 🔴 NICHT IM CODE VORHANDEN - MUSS NACHGERÜSTET WERDEN

11. **Code Refactoring Engine**
    - Module: `code_refactoring_engine.py`
    - Description: Provides tools for automated code refactoring.
    - Status: 🔴 NICHT IM CODE VORHANDEN - MUSS NACHGERÜSTET WERDEN
