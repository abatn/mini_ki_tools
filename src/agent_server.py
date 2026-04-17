from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import os
import json
import logging
from src.agent import Agent
from src.tools import ToolRegistry
from src.git_integration import GitIntegration
from src.long_term_memory import store_memory, search_memory
from src.batch_processor import BatchProcessor
from apscheduler.schedulers.background import BackgroundScheduler

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
    """Health check endpoint"""
    return {"status": "healthy", "tools": tool_registry.get_tool_list()}

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
        from src.embedding import get_embedding
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
        from src.embedding import get_embedding
        from src.long_term_memory import memory_collection
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 