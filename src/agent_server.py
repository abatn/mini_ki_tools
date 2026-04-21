# agent_server.py - Main FastAPI server
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import os
import json
import logging
from agent import Agent
from tools import ToolRegistry
from git_integration import GitIntegration
from long_term_memory import store_memory, search_memory
from batch_processor import BatchProcessor
from llm_provider import get_llm_manager
from provider_manager import get_provider_manager
from apscheduler.schedulers.background import BackgroundScheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mini KI Tools", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent and tools
tool_registry = ToolRegistry()
agent = Agent()
git_integration = GitIntegration()

try:
    batch_processor = BatchProcessor()
except:
    batch_processor = None

try:
    scheduler = BackgroundScheduler()
    scheduler.start()
except:
    scheduler = None

# Models
class Message(BaseModel):
    message: str
    context: Dict = {}
    mode: str = "tao"  # tao, tot, got, reflexion, plan_solve, pot, voyager

class ChatResponse(BaseModel):
    response: str
    history: List[Dict] = []

# Root endpoint - serve web UI
@app.get("/")
async def root():
    from pathlib import Path
    script_path = Path(__file__).resolve()
    app_root = str(script_path.parent.parent)
    html_path = os.path.join(app_root, "frontend", "build", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return {"message": "Mini KI Tools API", "version": "1.0.0"}

# Static files
@app.get("/static/{file_path:path}")
async def static_file(file_path: str):
    from fastapi.responses import FileResponse
    from pathlib import Path
    script_path = Path(__file__).resolve()
    app_root = str(script_path.parent.parent)
    base = os.path.join(app_root, "frontend", "build", "static")
    path = os.path.normpath(os.path.join(base, file_path))
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="File not found")

# Health check with LLM info
@app.get("/health")
async def health_check():
    try:
        from workspace import get_workspace_manager
        ws_manager = get_workspace_manager()
        workspace_info = {
            "workspace_path": ws_manager.get_workspace_path(),
            "read_only": ws_manager.is_read_only(),
            "max_file_size_mb": ws_manager.get_max_file_size() // (1024*1024),
            "execution_timeout": ws_manager.get_execution_timeout()
        }
    except:
        workspace_info = {"workspace_path": "/workspace"}

    try:
        llm_manager = get_llm_manager()
        provider = llm_manager.get_provider()
        llm_info = {
            "provider": llm_manager.get_current_provider_name(),
            "model": provider.get_default_model() if provider else None,
            "available": provider.is_available() if provider else False
        }
    except:
        llm_info = {"provider": "N/A", "available": False}

    return {"status": "ok", "workspace": workspace_info, "llm": llm_info}

# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: Message):
    if request.mode and request.mode != "tao":
        from reasoning_engine import get_reasoning_engine, ReasoningResult
        engine = get_reasoning_engine(request.mode)
        result = await engine.think(request.message, request.context)
        return ChatResponse(
            response=result.result or result.thought,
            history=[{"mode": request.mode, "steps": result.steps}]
        )
    result, history = agent.process_message(request.message)
    return ChatResponse(response=result, history=history)

# Get available tools
@app.get("/tools")
async def tools():
    return {"tools": tool_registry.get_tool_list()}

# Provider Manager endpoints
@app.get("/providers")
async def get_providers():
    from provider_manager import get_provider_manager
    manager = get_provider_manager()
    return manager.to_dict()

@app.post("/providers/check")
async def check_providers():
    from provider_manager import get_provider_manager
    import asyncio
    manager = get_provider_manager()
    await manager.check_all_providers(force=True)
    return manager.to_dict()

# Workspace config
@app.get("/workspace/config")
async def get_workspace_config():
    from workspace import get_workspace_manager
    return get_workspace_manager().get_config()

@app.post("/workspace/config")
async def update_workspace_config(config: dict):
    from workspace import get_workspace_manager
    ws = get_workspace_manager()
    for k, v in config.items():
        ws.set_config(k, v)
    return {"success": True}

# Git endpoints
@app.post("/api/git/commit")
async def git_commit(request: Dict):
    return await git_integration.commit(request.get("message", ""))

@app.post("/api/git/branch")
async def git_branch(request: Dict):
    return await git_integration.create_branch(request.get("branch_name", ""))

# Memory endpoints
@app.post("/memory/store")
async def store_mem(request: Dict):
    return store_memory(request.get("content", ""), request.get("metadata", {}))

@app.post("/memory/search")
async def search_mem(request: Dict):
    return search_memory(request.get("query", ""))

# Collaboration endpoints
@app.get("/api/collab/rooms")
async def list_rooms():
    from collaboration import collaboration_manager
    return {"rooms": [r.to_dict() for r in collaboration_manager.rooms.values()]}

# Export/Import endpoints
@app.get("/api/config/export")
async def export_config():
    from config_exporter import handle_export_command
    return await handle_export_command({})

@app.post("/api/config/import")
async def import_config(request: Dict):
    from config_exporter import handle_import_command
    return await handle_import_command(request)

# Sandbox endpoints
@app.post("/api/sandbox/execute")
async def sandbox_exec(request: Dict):
    from sandbox_manager import get_sandbox_manager
    return await get_sandbox_manager().execute(
        request.get("command", ""),
        request.get("files", []),
        request.get("env_vars", {}),
        request.get("user_id", "anonymous")
    )

@app.get("/api/sandbox/active")
async def active_sandboxes():
    from sandbox_manager import get_sandbox_manager
    return get_sandbox_manager().get_active()

# Audit endpoints
@app.post("/api/audit/log")
async def audit_log(request: Dict):
    from audit_logger import log_action
    return log_action(
        request.get("user_id", "anonymous"),
        request.get("action", ""),
        request.get("details", {})
    )

# Orchestrator endpoints
@app.post("/api/orchestrator/execute")
async def orchestrator_exec(request: Dict):
    from orchestrator import get_orchestrator
    orch = get_orchestrator()
    return await orch.execute_task(request.get("task", ""), request.get("context", {}))

@app.get("/api/orchestrator/roles")
async def orchestrator_roles():
    from orchestrator import AgentRole
    return {"roles": [r.value for r in AgentRole]}

# Self-healing endpoints
@app.post("/api/self-healing/run")
async def self_healing_run(request: Dict):
    from self_healing import get_self_healing_engine
    return await get_self_healing_engine().run(request.get("test_file", ""))

# MCP Marketplace endpoints
@app.get("/api/mcp/marketplace/servers")
async def mcp_servers():
    from mcp_marketplace import get_marketplace
    return get_marketplace().list_servers()

# Subagents endpoints
@app.post("/api/subagents/execute")
async def subagents_exec(request: Dict):
    from subagents import get_subagents
    return await get_subagents().execute(
        request.get("task", ""),
        request.get("agent_types", []),
        request.get("context", {})
    )

# LLM provider endpoints
@app.get("/api/llm/providers")
async def llm_providers():
    pm = get_provider_manager()
    return {"providers": pm.to_dict()}

@app.post("/api/llm/switch")
async def switch_llm(request: Dict):
    pm = get_provider_manager()
    provider_id = request.get("provider_id", "")
    if provider_id in pm.providers:
        pm.providers[provider_id].enabled = True
    return {"success": True}

# Provider Manager API Keys endpoints
@app.post("/api/llm/keys")
async def save_api_key(request: Dict):
    """Speichert API-Key für einen Provider verschlüsselt"""
    provider_id = request.get("provider_id", "")
    api_key = request.get("api_key", "")
    
    if not provider_id:
        return {"success": False, "error": "provider_id required"}
    
    if not api_key:
        return {"success": False, "error": "api_key required"}
    
    pm = get_provider_manager()
    success = pm.save_api_key(provider_id, api_key)
    
    return {"success": success}

@app.post("/api/llm/keys/test")
async def test_api_key(request: Dict):
    """Testet einen API-Key mit Validierung"""
    provider_id = request.get("provider_id", "")
    api_key = request.get("api_key", "")
    
    if not provider_id:
        return {"valid": False, "error": "provider_id required"}
    
    if not api_key:
        return {"valid": False, "error": "api_key required"}
    
    pm = get_provider_manager()
    
    # Temporär setzen und testen
    original_key = pm.providers.get(provider_id).api_key if provider_id in pm.providers else None
    pm.providers[provider_id].api_key = api_key
    
    import asyncio
    result = await pm.check_provider(provider_id)
    
    # Restore original if needed
    if original_key:
        pm.providers[provider_id].api_key = original_key
    
    return {
        "valid": result.status.value == "available",
        "latency": result.latency_ms if result.latency_ms < 999999 else None,
        "models": result.models[:10] if result.models else [],
        "error": None if result.status.value == "available" else f"Status: {result.status.value}"
    }

@app.delete("/api/llm/keys/{provider_id}")
async def delete_api_key(provider_id: str):
    """Entfernt API-Key für einen Provider"""
    pm = get_provider_manager()
    success = pm.remove_api_key(provider_id)
    return {"success": success}

# Slash Commands endpoints
@app.post("/api/commands/execute")
async def execute_command(request: Dict):
    from slash_commands import get_command_registry
    registry = get_command_registry()
    result = await registry.execute_command(request.get("command", ""), request.get("args", ""))
    return {"success": result.success, "output": result.output}

@app.get("/api/commands/list")
async def list_commands():
    from slash_commands import get_command_registry
    registry = get_command_registry()
    return {"commands": [{"name": n, "description": c.description} for n, c in registry._commands.items()]}

# Team Management endpoints
@app.post("/api/teams/create")
async def create_team(request: Dict):
    from team_management import get_team_manager
    manager = get_team_manager()
    team = manager.create_team(request.get("team_name", "default"), request.get("lead", "architect"))
    return {"success": True, "team_id": team.id}

@app.post("/api/teams/{team_id}/spawn")
async def spawn_teammate(team_id: str, request: Dict):
    from team_management import get_team_manager
    manager = get_team_manager()
    result = manager.spawn_teammate(team_id, request.get("type", "coder"))
    return {"success": result.success}

@app.get("/api/teams/{team_id}/status")
async def team_status(team_id: str):
    from team_management import get_team_manager
    manager = get_team_manager()
    team = manager.get_team(team_id)
    if not team:
        return {"error": "Team not found"}
    return {"team_id": team.id, "teammates": [{"id": t.id, "status": t.status} for t in team.teammates]}

# Run server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)