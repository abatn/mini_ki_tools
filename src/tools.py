import os
import subprocess
import requests
import json
import tempfile
from typing import Dict, Any, List, Callable, Awaitable, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Import workspace manager for path validation
try:
    from workspace import get_workspace_manager, get_workspace_path, validate_path
    WORKSPACE_ENABLED = True
except ImportError:
    WORKSPACE_ENABLED = False
    def get_workspace_path():
        return "/workspace"
    def validate_path(path):
        return (True, "")

# Import permissions system
try:
    from agent_permissions import (
        get_permission_store, 
        check_tool_permission,
        PermissionCheckResult,
        PermissionAction
    )
    PERMISSIONS_ENABLED = True
except ImportError:
    PERMISSIONS_ENABLED = False
    PermissionCheckResult = None
    PermissionAction = None
    def check_tool_permission(agent_name: str, tool_name: str) -> bool:
        return True

# Permission callback for asking user (to be set by UI)
_ask_user_callback: Optional[Callable[[str, str], Awaitable[bool]]] = None

def set_ask_user_callback(callback: Callable[[str, str], Awaitable[bool]]):
    """Set callback for asking user permission"""
    global _ask_user_callback
    _ask_user_callback = callback

async def check_permission_with_ask(
    agent_name: str, 
    tool_name: str, 
    tool_description: str
) -> tuple[bool, str]:
    """
    Check tool permission, ask user if action is 'ask'.
    Returns (allowed, reason)
    """
    if not PERMISSIONS_ENABLED:
        return (True, "Permissions not enabled")
    
    store = get_permission_store()
    result = store.check_tool(agent_name, tool_name)
    
    if result.action == PermissionAction.ALLOW:
        return (True, result.reason)
    
    if result.action == PermissionAction.DENY:
        return (False, f"Tool '{tool_name}' is denied: {result.reason}")
    
    # ASK - need user confirmation
    if _ask_user_callback is None:
        return (False, f"Tool '{tool_name}' requires user confirmation but no callback set")
    
    try:
        allowed = await _ask_user_callback(
            tool_name, 
            f"Der Agent möchte '{tool_name}' ausführen. Erlauben?"
        )
        return (allowed, "User confirmed" if allowed else "User denied")
    except Exception as e:
        return (False, f"Error asking user: {e}")

class Tool:
    """Base class for all tools"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def execute(self, **kwargs) -> Any:
        raise NotImplementedError("Subclasses must implement execute method")

class ReadFileTool(Tool):
    """Tool to read files within workspace"""
    def __init__(self):
        super().__init__("read_file", "Read content from a file within workspace")
    
    async def execute_async(self, agent_name: str, filename: str, encoding: str = "utf-8") -> str:
        """Async version with permission check"""
        # Check permission
        allowed, reason = await check_permission_with_ask(
            agent_name, "read_file", "Datei lesen"
        )
        if not allowed:
            return f"Permission denied: {reason}"
        
        return self.execute(filename=filename, encoding=encoding)
    
    def execute(self, filename: str, encoding: str = "utf-8") -> str:
        try:
            # Resolve path within workspace
            if WORKSPACE_ENABLED:
                is_valid, error = validate_path(filename)
                if not is_valid:
                    return f"Error: {error}"
                
                # Resolve to workspace path
                from workspace import get_workspace_manager
                ws_manager = get_workspace_manager()
                filename = ws_manager.resolve_path(filename)
                
                # Check file size
                if os.path.exists(filename):
                    file_size = os.path.getsize(filename)
                    if file_size > ws_manager.get_max_file_size():
                        return f"Error: File too large (max {ws_manager.get_max_file_size() // (1024*1024)}MB)"
            
            with open(filename, 'r', encoding=encoding) as file:
                content = file.read()
            return content
        except Exception as e:
            return f"Error reading file {filename}: {str(e)}"

class WriteFileTool(Tool):
    """Tool to write content to files within workspace"""
    def __init__(self):
        super().__init__("write_file", "Write content to a file within workspace")
    
    async def execute_async(self, agent_name: str, filename: str, content: str, encoding: str = "utf-8") -> str:
        """Async version with permission check"""
        allowed, reason = await check_permission_with_ask(
            agent_name, "write_file", "Datei schreiben"
        )
        if not allowed:
            return f"Permission denied: {reason}"
        
        return self.execute(filename=filename, content=content, encoding=encoding)
    
    def execute(self, filename: str, content: str, encoding: str = "utf-8") -> str:
        try:
            # Check read-only mode
            if WORKSPACE_ENABLED:
                from workspace import get_workspace_manager
                ws_manager = get_workspace_manager()
                if ws_manager.is_read_only():
                    return "Error: Workspace is in read-only mode"
                
                is_valid, error = validate_path(filename)
                if not is_valid:
                    return f"Error: {error}"
                
                # Resolve to workspace path
                filename = ws_manager.resolve_path(filename)
            
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding=encoding) as file:
                file.write(content)
            return f"Successfully wrote to {filename}"
        except Exception as e:
            return f"Error writing to file {filename}: {str(e)}"

class ExecuteCodeTool(Tool):
    """Tool to execute Python code within workspace"""
    def __init__(self):
        super().__init__("execute_code", "Execute Python code within workspace")
    
    async def execute_async(self, agent_name: str, code: str, timeout: int = None) -> str:
        """Async version with permission check"""
        allowed, reason = await check_permission_with_ask(
            agent_name, "execute_code", "Code ausführen"
        )
        if not allowed:
            return f"Permission denied: {reason}"
        
        return self.execute(code=code, timeout=timeout)
    
    def execute(self, code: str, timeout: int = None) -> str:
        try:
            # Get timeout from workspace config if available
            if WORKSPACE_ENABLED and timeout is None:
                from workspace import get_workspace_manager
                timeout = get_workspace_manager().get_execution_timeout()
            elif timeout is None:
                timeout = 30
            
            # Create temporary file in workspace
            if WORKSPACE_ENABLED:
                workspace_path = get_workspace_path()
            else:
                workspace_path = "/workspace"
            
            temp_file = os.path.join(workspace_path, f"temp_{os.getpid()}.py")
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Execute the code
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace_path
            )
            
            # Clean up
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return f"Code executed successfully:\n{result.stdout}"
            else:
                return f"Code execution failed:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "Code execution timed out"
        except Exception as e:
            return f"Error executing code: {str(e)}"

class HttpRequestTool(Tool):
    """Tool to make HTTP requests"""
    def __init__(self):
        super().__init__("http_request", "Make HTTP requests")
    
    async def execute_async(self, agent_name: str, url: str, method: str = "GET", 
                           headers: Dict[str, str] = None, data: Dict[str, Any] = None) -> str:
        """Async version with permission check"""
        allowed, reason = await check_permission_with_ask(
            agent_name, "http_request", "HTTP-Anfrage senden"
        )
        if not allowed:
            return f"Permission denied: {reason}"
        
        return self.execute(url=url, method=method, headers=headers, data=data)
    
    def execute(self, url: str, method: str = "GET", headers: Dict[str, str] = None, 
                data: Dict[str, Any] = None) -> str:
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                return f"Unsupported HTTP method: {method}"
            
            return f"Status: {response.status_code}\nHeaders: {dict(response.headers)}\nContent: {response.text}"
        except Exception as e:
            return f"Error making HTTP request: {str(e)}"

class RunCommandTool(Tool):
    """Tool to run terminal commands within workspace"""
    def __init__(self):
        super().__init__("run_command", "Run terminal commands within workspace")
    
    async def execute_async(self, agent_name: str, command: str, timeout: int = 30) -> str:
        """Async version with permission check"""
        allowed, reason = await check_permission_with_ask(
            agent_name, "run_command", "Befehl ausführen"
        )
        if not allowed:
            return f"Permission denied: {reason}"
        
        return self.execute(command=command, timeout=timeout)
    
    def execute(self, command: str, timeout: int = 30) -> str:
        try:
            # Set working directory to workspace
            if WORKSPACE_ENABLED:
                cwd = get_workspace_path()
            else:
                cwd = "/workspace"
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            if result.returncode == 0:
                return f"Command executed successfully:\n{result.stdout}"
            else:
                return f"Command failed with return code {result.returncode}:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error running command: {str(e)}"

class ReadCSVTool(Tool):
    """Tool to read CSV files within workspace"""
    def __init__(self):
        super().__init__("read_csv", "Read CSV file content within workspace")
    
    def execute(self, filename: str, delimiter: str = ",") -> str:
        try:
            # Validate path within workspace
            if WORKSPACE_ENABLED:
                is_valid, error = validate_path(filename)
                if not is_valid:
                    return f"Error: {error}"
                
                from workspace import get_workspace_manager
                filename = get_workspace_manager().resolve_path(filename)
            
            import csv
            with open(filename, 'r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter=delimiter)
                rows = list(reader)
                return f"CSV content (first 5 rows):\n{json.dumps(rows[:5], indent=2)}"
        except Exception as e:
            return f"Error reading CSV file {filename}: {str(e)}"

class ToolRegistry:
    """Registry for all available tools"""
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register all default tools"""
        self.register_tool(ReadFileTool())
        self.register_tool(WriteFileTool())
        self.register_tool(ExecuteCodeTool())
        self.register_tool(HttpRequestTool())
        self.register_tool(RunCommandTool())
        self.register_tool(ReadCSVTool())
    
    def register_tool(self, tool: Tool):
        """Register a new tool"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Tool:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def get_tool_list(self) -> List[Dict[str, str]]:
        """Get list of all available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools.values()
        ]