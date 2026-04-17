import os
import subprocess
import requests
import json
import tempfile
from typing import Dict, Any, List
from pathlib import Path

class Tool:
    """Base class for all tools"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def execute(self, **kwargs) -> Any:
        raise NotImplementedError("Subclasses must implement execute method")

class ReadFileTool(Tool):
    """Tool to read files"""
    def __init__(self):
        super().__init__("read_file", "Read content from a file")
    
    def execute(self, filename: str, encoding: str = "utf-8") -> str:
        try:
            with open(filename, 'r', encoding=encoding) as file:
                content = file.read()
            return content
        except Exception as e:
            return f"Error reading file {filename}: {str(e)}"

class WriteFileTool(Tool):
    """Tool to write content to files"""
    def __init__(self):
        super().__init__("write_file", "Write content to a file")
    
    def execute(self, filename: str, content: str, encoding: str = "utf-8") -> str:
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding=encoding) as file:
                file.write(content)
            return f"Successfully wrote to {filename}"
        except Exception as e:
            return f"Error writing to file {filename}: {str(e)}"

class ExecuteCodeTool(Tool):
    """Tool to execute Python code"""
    def __init__(self):
        super().__init__("execute_code", "Execute Python code")
    
    def execute(self, code: str, timeout: int = 30) -> str:
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Execute the code
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
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
    """Tool to run terminal commands"""
    def __init__(self):
        super().__init__("run_command", "Run terminal commands")
    
    def execute(self, command: str, timeout: int = 30) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
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
    """Tool to read CSV files"""
    def __init__(self):
        super().__init__("read_csv", "Read CSV file content")
    
    def execute(self, filename: str, delimiter: str = ",") -> str:
        try:
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