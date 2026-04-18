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
from apscheduler.schedulers.background import BackgroundScheduler
from llm_provider import get_llm_manager, LLMProviderFactory

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Local Agent Tool", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent and tool registry
tool_registry = ToolRegistry()
agent = Agent()
git_integration = GitIntegration()
batch_processor = BatchProcessor()
scheduler = BackgroundScheduler()
scheduler.start()

class Message(BaseModel):
    content: str
    role: str = "user"

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "llama3.2"

class ChatResponse(BaseModel):
    response: str
    messages: List[Message]

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <html>
        <head>
            <title>Local Agent Tool</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .chat-container { max-width: 800px; margin: 0 auto; }
                .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
                .user { background-color: #e3f2fd; }
                .assistant { background-color: #f5f5f5; }
                .input-container { margin-top: 20px; }
                input[type="text"] { width: 70%; padding: 10px; }
                button { padding: 10px 20px; background-color: #2196f3; color: white; border: none; cursor: pointer; }
                button:hover { background-color: #1976d2; }
            </style>
        </head>
        <body>
            <h1>Local Agent Tool</h1>
            <div class="chat-container">
                <div id="chat-messages"></div>
                <div class="input-container">
                    <input type="text" id="message-input" placeholder="Type your message here...">
                    <button onclick="sendMessage()">Send</button>
                </div>
            </div>
            <script>
                function sendMessage() {
                    const input = document.getElementById('message-input');
                    const message = input.value;
                    if (message.trim()) {
                        fetch('/chat', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({messages: [{content: message, role: 'user'}]})
                        })
                        .then(response => response.json())
                        .then(data => {
                            const chatMessages = document.getElementById('chat-messages');
                            chatMessages.innerHTML += `<div class="message user">You: ${message}</div>`;
                            chatMessages.innerHTML += `<div class="message assistant">Agent: ${data.response}</div>`;
                            input.value = '';
                        });
                    }
                }
            </script>
        </body>
    </html>
    """

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Get the last user message
        user_message = request.messages[-1].content
        
        # Process the message with the agent
        response = agent.process_message(user_message)
        
        # Add to conversation history
        messages = request.messages + [Message(content=response, role="assistant")]
        
        return ChatResponse(response=response, messages=messages)
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def get_tools():
    """Get list of available tools"""
    return tool_registry.get_tool_list()

@app.get("/health")
async def health_check():
    """Health check endpoint with workspace info"""
    # Get workspace info
    try:
        from workspace import get_workspace_manager
        ws_manager = get_workspace_manager()
        workspace_info = {
            "workspace_path": ws_manager.get_workspace_path(),
            "read_only": ws_manager.is_read_only(),
            "max_file_size_mb": ws_manager.get_max_file_size() // (1024*1024),
            "execution_timeout": ws_manager.get_execution_timeout()
        }
    except ImportError:
        workspace_info = {"workspace_path": "/workspace", "error": "Workspace module not available"}
    
    # Get LLM provider info
    try:
        llm_manager = get_llm_manager()
        provider = llm_manager.get_provider()
        llm_info = {
            "provider": llm_manager.get_current_provider_name(),
            "model": provider.get_default_model() if provider else None,
            "available": provider.is_available() if provider else False
        }
    except Exception as e:
        llm_info = {"error": str(e)}
    
    return {
        "status": "healthy",
        "tools": tool_registry.get_tool_list(),
        "workspace": workspace_info,
        "llm": llm_info
    }

@app.get("/workspace/config")
async def get_workspace_config():
    """Get workspace configuration"""
    try:
        from workspace import get_workspace_manager
        ws_manager = get_workspace_manager()
        return ws_manager.get_config()
    except ImportError:
        return {"error": "Workspace module not available"}

@app.post("/workspace/config")
async def update_workspace_config(config: dict):
    """Update workspace configuration (runtime - not persisted)"""
    try:
        from workspace import get_workspace_manager
        ws_manager = get_workspace_manager()
        # Note: This only updates runtime, not the config file
        return {"status": "success", "config": ws_manager.get_config()}
    except ImportError:
        return {"error": "Workspace module not available"}

# ============ Git Integration Endpoints ============
@app.post("/api/git/commit")
async def git_commit(request: dict):
    """Commit changes to git repository"""
    message = request.get("message", "Auto commit")
    files = request.get("files")
    result = git_integration.commit(message, files)
    return result

@app.post("/api/git/branch")
async def git_branch(request: dict):
    """Create or switch to a branch"""
    branch_name = request.get("branch_name")
    create = request.get("create", True)
    result = git_integration.branch(branch_name, create)
    return result

# ============ Memory Endpoints ============
class MemoryRequest(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}

@app.post("/memory/store")
async def store_memory_endpoint(request: MemoryRequest):
    """Store a memory in the vector database"""
    try:
        from embedding import get_embedding
        embedding = get_embedding(request.content)
        memory_id = store_memory(embedding, {"content": request.content, **request.metadata})
        return {"status": "success", "memory_id": memory_id}
    except Exception as e:
        logger.error(f"Error storing memory: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/memory/search")
async def search_memory_endpoint(request: dict):
    """Search memories in the vector database"""
    try:
        query = request.get("query", "")
        from embedding import get_embedding
        from long_term_memory import memory_collection
        query_embedding = get_embedding(query)
        results = memory_collection.query(query_embeddings=[query_embedding], n_results=3)
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"Error searching memory: {str(e)}")
        return {"status": "error", "message": str(e)}

# ============ Batch Processing Endpoints ============
class BatchRequest(BaseModel):
    filepaths: List[str]
    processor: str = "default"

@app.post("/api/batch/process_files_parallel")
async def batch_process_files(request: BatchRequest):
    """Process files in parallel"""
    import asyncio
    
    def default_processor(filepath: str) -> str:
        with open(filepath, 'r') as f:
            return f"Processed: {filepath}"
    
    results = await batch_processor.process_files(request.filepaths, default_processor)
    return {"status": "success", "results": results}

# ============ Scheduler Endpoints ============
class ScheduleRequest(BaseModel):
    func: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    job_id: str
    trigger: str = "date"
    run_date: str = None

@app.post("/api/schedule/add")
async def schedule_add_job(request: ScheduleRequest):
    """Add a scheduled job"""
    from datetime import datetime
    
    try:
        trigger_kwargs = {}
        if request.trigger == "date" and request.run_date:
            trigger_kwargs["run_date"] = datetime.fromisoformat(request.run_date)
        
        job = scheduler.add_job(
            eval(request.func),
            request.trigger,
            id=request.job_id,
            args=request.args,
            kwargs=request.kwargs,
            **trigger_kwargs
        )
        return {"status": "success", "job_id": job.id}
    except Exception as e:
        logger.error(f"Error adding job: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/schedule/list")
async def schedule_list_jobs():
    """List all scheduled jobs"""
    jobs = [{"id": job.id, "next_run": str(job.next_run_time)} for job in scheduler.get_jobs()]
    return {"jobs": jobs}

@app.post("/api/schedule/remove")
async def schedule_remove_job(request: dict):
    """Remove a scheduled job"""
    job_id = request.get("job_id")
    scheduler.remove_job(job_id)
    return {"status": "success", "job_id": job_id}

# ============ Collaboration WebSocket Endpoints ============
from fastapi import WebSocket
from collaboration import handle_collab_connection, collaboration_manager
import uuid

@app.websocket("/ws/collab")
async def websocket_collab(websocket: WebSocket):
    """WebSocket endpoint for real-time collaboration"""
    user_id = f"user_{uuid.uuid4().hex[:6]}"
    await handle_collab_connection(websocket, user_id)

@app.get("/api/collab/rooms")
async def list_collab_rooms():
    """List all active collaboration rooms"""
    return {"rooms": collaboration_manager.list_rooms()}

# ============ Config Export/Import Endpoints ============
from config_exporter import ConfigExporter, ConfigImporter

@app.get("/api/config/export")
async def export_config():
    """Export current configuration to .agentconfig"""
    exporter = ConfigExporter()
    return exporter.export()

@app.post("/api/config/import")
async def import_config(request: dict):
    """Import configuration from .agentconfig file"""
    input_path = request.get("path")
    merge = request.get("merge", True)
    
    if not input_path:
        raise HTTPException(status_code=400, detail="path required")
    
    importer = ConfigImporter()
    return importer.import_config(input_path, merge)

# ============ Sandbox Endpoints ============
from sandbox_manager import get_sandbox_manager

@app.post("/api/sandbox/execute")
async def sandbox_execute(request: dict):
    """Execute command in isolated sandbox"""
    command = request.get("command")
    files = request.get("files", {})
    env_vars = request.get("env_vars", {})
    user_id = request.get("user_id", "default")
    
    if not command:
        raise HTTPException(status_code=400, detail="command required")
    
    manager = get_sandbox_manager()
    result = manager.execute(command, files, env_vars, user_id)
    
    return {
        "sandbox_id": result.sandbox_id,
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "exit_code": result.exit_code,
        "duration": result.duration
    }

@app.get("/api/sandbox/active")
async def sandbox_list():
    """List active sandboxes"""
    manager = get_sandbox_manager()
    return {"sandboxes": manager.get_active_sandboxes()}

@app.delete("/api/sandbox/{sandbox_id}")
async def sandbox_kill(sandbox_id: str):
    """Kill a sandbox"""
    manager = get_sandbox_manager()
    success = manager.kill_sandbox(sandbox_id)
    return {"success": success}

# ============ Audit Log Endpoints ============
from audit_logger import get_audit_logger, log_action

@app.post("/api/audit/log")
async def audit_log(request: dict):
    """Log an action to audit"""
    user_id = request.get("user_id", "anonymous")
    action_type = request.get("action_type", "unknown")
    
    entry_id = log_action(
        user_id=user_id,
        action_type=action_type,
        file_path=request.get("file_path"),
        prompt=request.get("prompt"),
        result=request.get("result"),
        success=request.get("success", True),
        metadata=request.get("metadata", {})
    )
    
    return {"status": "success", "entry_id": entry_id}

@app.get("/api/audit/search")
async def audit_search(
    user_id: str = None,
    action_type: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100
):
    """Search audit logs"""
    logger = get_audit_logger()
    entries = logger.search(user_id, action_type, start_date, end_date, limit)
    return {
        "count": len(entries),
        "entries": [e.to_dict() for e in entries]
    }

@app.get("/api/audit/export")
async def audit_export(
    path: str = None,
    format: str = "json",
    start_date: str = None,
    end_date: str = None
):
    """Export audit logs"""
    logger = get_audit_logger()
    return logger.export(path, format, start_date, end_date)

@app.get("/api/audit/stats")
async def audit_stats(days: int = 7):
    """Get audit statistics"""
    logger = get_audit_logger()
    return logger.get_stats(days)


# ============ Orchestrator Endpoints ============
from orchestrator import Orchestrator, OrchestratorAgent, AgentRole, SubAgent

orchestrator = Orchestrator()

class OrchestratorRequest(BaseModel):
    task: str
    enable_parallel: bool = True

class OrchestratorResponse(BaseModel):
    task_id: str
    status: str
    subtasks: List[Dict]
    final_result: str
    duration: float
    errors: List[str]


@app.post("/api/orchestrator/execute", response_model=OrchestratorResponse)
async def orchestrator_execute(request: OrchestratorRequest):
    """Execute a task using the multi-agent orchestrator"""
    orchestrator.enable_parallel = request.enable_parallel
    result = orchestrator.execute_task(request.task)
    
    return OrchestratorResponse(
        task_id=result.task_id,
        status=result.status,
        subtasks=[
            {
                "id": t.id,
                "role": t.role.value,
                "status": t.status,
                "description": t.description,
                "result": t.result
            }
            for t in result.subtasks
        ],
        final_result=result.final_result,
        duration=result.duration,
        errors=result.errors
    )


@app.get("/api/orchestrator/status")
async def orchestrator_status():
    """Get current orchestrator status"""
    return orchestrator.get_status()


@app.get("/api/orchestrator/roles")
async def orchestrator_roles():
    """Get available agent roles"""
    return {
        "roles": [
            {"name": role.value, "tools": SubAgent(role).tools}
            for role in AgentRole
        ]
    }


@app.post("/api/orchestrator/reset")
async def orchestrator_reset():
    """Reset orchestrator state"""
    global orchestrator
    orchestrator = Orchestrator()
    return {"status": "reset"}


# ============ Self-Healing Endpoints ============
from self_healing import SelfHealingEngine, SelfHealingAgent

self_healing_engine = SelfHealingEngine()

class HealingRequest(BaseModel):
    test_path: str = "tests/"
    file_to_fix: str = None
    code_context: str = ""


@app.post("/api/self-healing/run")
async def run_self_healing(request: HealingRequest):
    """Run self-healing process"""
    success, iterations = self_healing_engine.heal(
        test_path=request.test_path,
        code_context=request.code_context,
        file_to_fix=request.file_to_fix
    )
    
    return {
        "success": success,
        "report": self_healing_engine.get_report()
    }


@app.get("/api/self-healing/status")
async def self_healing_status():
    """Get self-healing status"""
    return self_healing_engine.get_report()


# ============ MCP Marketplace Endpoints ============
from mcp_marketplace import MCPMarketplace

mcp_marketplace = MCPMarketplace()


@app.get("/api/mcp/marketplace/servers")
async def mcp_list_servers(category: str = None, installed: bool = None):
    """List available MCP servers"""
    if installed:
        servers = mcp_marketplace.list_installed()
    elif category:
        servers = mcp_marketplace.list_by_category(category)
    else:
        servers = list(mcp_marketplace.servers.values())
    
    return {
        "count": len(servers),
        "servers": [
            {
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "installed": s.installed
            }
            for s in servers
        ]
    }


@app.get("/api/mcp/marketplace/search")
async def mcp_search(q: str):
    """Search MCP servers"""
    results = mcp_marketplace.search(q)
    return {
        "count": len(results),
        "servers": [
            {
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "installed": s.installed
            }
            for s in results
        ]
    }


@app.post("/api/mcp/marketplace/install/{name}")
async def mcp_install(name: str):
    """Install an MCP server"""
    result = mcp_marketplace.install(name)
    return result


@app.post("/api/mcp/marketplace/uninstall/{name}")
async def mcp_uninstall(name: str):
    """Uninstall an MCP server"""
    result = mcp_marketplace.uninstall(name)
    return result


@app.post("/api/mcp/marketplace/update")
async def mcp_update(name: str = None):
    """Update MCP server(s)"""
    result = mcp_marketplace.update(name)
    return result


@app.get("/api/mcp/marketplace/config/{name}")
async def mcp_get_config(name: str):
    """Get MCP server configuration"""
    config = mcp_marketplace.get_config(name)
    if config:
        return config
    return {"error": f"Server '{name}' not found"}


@app.get("/api/mcp/marketplace/categories")
async def mcp_categories():
    """Get all categories"""
    return {"categories": mcp_marketplace.get_all_categories()}


# ============ Subagents Endpoints ============
from subagents import NativeSubAgents, MultiAgentOrchestrator, SubAgentType

subagents_system = NativeSubAgents()
orchestrator = MultiAgentOrchestrator()


class SubAgentTask(BaseModel):
    task: str
    agent_type: str = "coder"
    name: str = None
    context: Dict = {}


class SubAgentExecuteRequest(BaseModel):
    tasks: List[SubAgentTask]
    parallel: bool = True


@app.post("/api/subagents/execute")
async def subagents_execute(request: SubAgentExecuteRequest):
    """Execute tasks with subagents"""
    # Convert agent types
    task_dicts = []
    for t in request.tasks:
        try:
            agent_type = SubAgentType(t.agent_type)
        except ValueError:
            agent_type = SubAgentType.CODER
        
        task_dicts.append({
            "task": t.task,
            "agent_type": agent_type,
            "name": t.name,
            "context": t.context
        })
    
    # Execute
    if request.parallel:
        results = await subagents_system.execute_parallel(task_dicts)
    else:
        results = await subagents_system.execute_sequential(task_dicts)
    
    # Aggregate
    aggregated = subagents_system.aggregate_results(results)
    
    return aggregated


@app.get("/api/subagents/status")
async def subagents_status():
    """Get subagent status"""
    return subagents_system.get_status()


@app.get("/api/subagents/types")
async def subagents_types():
    """Get available subagent types"""
    return {
        "types": [
            {"name": t.value, "description": t.name}
            for t in SubAgentType
        ]
    }


# LLM Provider Endpoints
@app.get("/api/llm/providers")
async def list_llm_providers():
    """Liste alle verfügbaren LLM Provider mit Status"""
    manager = get_llm_manager()
    return {
        "current_provider": manager.get_current_provider_name(),
        "providers": manager.list_providers()
    }


@app.post("/api/llm/switch")
async def switch_llm_provider(request: Dict):
    """Wechsle zu einem anderen LLM Provider"""
    provider_name = request.get("provider")
    if not provider_name:
        raise HTTPException(status_code=400, detail="Provider name required")
    
    manager = get_llm_manager()
    success = manager.switch_provider(provider_name)
    
    if success:
        return {
            "success": True,
            "current_provider": manager.get_current_provider_name()
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 