# Thought-Action-Observation Loop Implementation
# Professionelle TAO-Loop-Lösung vergleichbar mit Cline/Kilo

import json
import re
import requests
import os
import subprocess
import tempfile
import csv
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Import LLM Provider (zentrale Abstraktion)
from llm_provider import get_llm_manager, LLMProvider


class ToolName(Enum):
    """Verfügbare Tools"""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE_CODE = "execute_code"
    READ_CSV = "read_csv"
    HTTP_REQUEST = "http_request"
    RUN_COMMAND = "run_command"


@dataclass
class ToolCall:
    """Tool-Aufruf mit Parametern"""
    tool: ToolName
    arguments: Dict[str, Any]
    result: Optional[str] = None
    success: bool = False


@dataclass
class TAOState:
    """State einer TAO-Iteration"""
    iteration: int
    thought: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    final_result: Optional[str] = None


class TAOLoop:
    """
    Thought-Action-Observation Loop.
    - think() ruft Ollama (llama3.2) auf
    - act() führt Tools aus (write_file, read_file, execute_code, read_csv, http_request, run_command)
    - observe() sammelt Ergebnisse
    """
    
    # Fallback code templates when Ollama is not available
    FALLBACK_TEMPLATES = {
        "fibonacci": '''def fib(n):
    """Calculate nth Fibonacci number"""
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

# Test: Print first 10 Fibonacci numbers
if __name__ == "__main__":
    for i in range(10):
        print(f"fib({i}) = {fib(i)}")''',
        
        "hello": 'print("Hello, World!")',
        
        "sort": '''def bubble_sort(arr):
    """Sort array using bubble sort"""
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

if __name__ == "__main__":
    test = [64, 34, 25, 12, 22, 11, 90]
    print(f"Sorted: {bubble_sort(test)}")''',
        
        "default": '''# Auto-generated code
# User request: {request}

def main():
    print("Code generated for: {request}")

if __name__ == "__main__":
    main()'''
    }
    
    def __init__(
        self,
        model: str = None,
        max_iterations: int = 10,
        timeout: int = 30,
        llm_manager: LLMProvider = None
    ):
        # Get model from environment variable or use provider's default
        # This ensures central configuration through LLM_MODEL env var
        import os
        if model is None:
            model = os.environ.get("LLM_MODEL")
        
        self.model = model  # Will be resolved after provider init
        self.max_iterations = max_iterations
        self.timeout = timeout
        self._session = requests.Session()
        self._session.timeout = timeout
        self.history: List[TAOState] = []
        self._llm_manager = llm_manager or get_llm_manager()
        self._fallback_tool_call = None  # For fallback mode direct execution
        
        # Resolve model after provider is initialized
        if self.model is None:
            provider = self._llm_manager.get_provider()
            if provider:
                self.model = provider.get_default_model()
    
    def _check_llm_available(self) -> bool:
        """Check if LLM provider is available"""
        provider = self._llm_manager.get_provider()
        if provider:
            return provider.is_available()
        return False
    
    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Ruft LLM Provider auf (zentrale Abstraktion)"""
        return self._llm_manager.generate(prompt, system_prompt, model=self.model)
    
    def _parse_tool_calls(self, response: str) -> List[ToolCall]:
        """Parse Tool-Aufrufe aus LLM-Response"""
        tool_calls = []
        
        # Match patterns like: write_file("test.py", "print('hello')")
        patterns = [
            r'(\w+)\s*\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*\)',
            r'(\w+)\s*\(\s*"([^"]+)"\s*\)',
            r'(\w+)\s*\(\s*([^\)]+)\s*\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response)
            for match in matches:
                tool_name = match[0].strip()
                
                tool_enum = None
                for tn in ToolName:
                    if tn.value == tool_name or tn.name.lower() == tool_name.lower():
                        tool_enum = tn
                        break
                
                if tool_enum:
                    args = {}
                    if len(match) >= 2:
                        if tool_enum == ToolName.WRITE_FILE:
                            args = {"filename": match[1], "content": match[2] if len(match) > 2 else ""}
                        elif tool_enum == ToolName.READ_FILE:
                            args = {"filename": match[1]}
                        elif tool_enum == ToolName.EXECUTE_CODE:
                            args = {"code": match[1]}
                        elif tool_enum == ToolName.READ_CSV:
                            args = {"filename": match[1]}
                        elif tool_enum == ToolName.HTTP_REQUEST:
                            args = {"url": match[1]}
                        elif tool_enum == ToolName.RUN_COMMAND:
                            args = {"command": match[1]}
                    
                    if args:
                        tool_calls.append(ToolCall(tool=tool_enum, arguments=args))
        
        return tool_calls
    
    def _execute_tool(self, tool_call: ToolCall) -> str:
        """Führt einen Tool-Aufruf aus mit Workspace-Pfad-Validierung"""
        tool = tool_call.tool
        args = tool_call.arguments
        
        # Import workspace manager
        try:
            from workspace import get_workspace_manager, get_workspace_path, validate_path
            ws_manager = get_workspace_manager()
            workspace_path = get_workspace_path()
            workspace_enabled = True
        except ImportError:
            workspace_path = "/workspace"
            workspace_enabled = False
        
        try:
            if tool == ToolName.WRITE_FILE:
                filename = args.get("filename", "")
                content = args.get("content", "")
                
                # Validate path within workspace
                if workspace_enabled:
                    is_valid, error = validate_path(filename)
                    if not is_valid:
                        return f"Error: {error}"
                    filename = ws_manager.resolve_path(filename)
                
                os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Successfully wrote to {filename}"
            
            elif tool == ToolName.READ_FILE:
                filename = args.get("filename", "")
                
                # Validate path within workspace
                if workspace_enabled:
                    is_valid, error = validate_path(filename)
                    if not is_valid:
                        return f"Error: {error}"
                    filename = ws_manager.resolve_path(filename)
                
                with open(filename, 'r', encoding='utf-8') as f:
                    return f.read()
            
            elif tool == ToolName.EXECUTE_CODE:
                code = args.get("code", "")
                
                # Create temp file in workspace
                temp_file = os.path.join(workspace_path, f"temp_{os.getpid()}.py")
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                result = subprocess.run(
                    ['python', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=workspace_path
                )
                os.unlink(temp_file)
                
                if result.returncode == 0:
                    return f"Output:\n{result.stdout}"
                else:
                    return f"Error:\n{result.stderr}"
            
            elif tool == ToolName.READ_CSV:
                filename = args.get("filename", "")
                
                # Validate path within workspace
                if workspace_enabled:
                    is_valid, error = validate_path(filename)
                    if not is_valid:
                        return f"Error: {error}"
                    filename = ws_manager.resolve_path(filename)
                
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    return f"CSV ({len(rows)} rows):\n" + "\n".join(str(r) for r in rows[:10])
            
            elif tool == ToolName.HTTP_REQUEST:
                url = args.get("url", "")
                response = requests.get(url, timeout=self.timeout)
                return f"Status: {response.status_code}\nContent: {response.text[:500]}"
            
            elif tool == ToolName.RUN_COMMAND:
                command = args.get("command", "")
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=workspace_path
                )
                return f"Output:\n{result.stdout}\nErrors:\n{result.stderr}"
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def think(self, user_input: str, context: str = "") -> str:
        """Denke über die Eingabe nach - ruft LLM Provider auf."""
        if not self._check_llm_available():
            return f"DIRECT_ANSWER: LLM not available. Please check your configuration."
        
        system_prompt = """You are an AI assistant that analyzes user requests and decides how to respond.

DECISION RULE:
- If the request is purely conversational (greetings like "hallo", "hi", "hello", thanks, apologies, small talk, general knowledge questions without code/file context), respond DIRECTLY without tools
- If the request involves code, files, web searches, or actual work, use appropriate tools

Available tools:
- write_file(filename, content): Write content to a file
- read_file(filename): Read content from a file
- execute_code(code): Execute Python code
- read_csv(filename): Read CSV file
- http_request(url): Make HTTP request
- run_command(command): Run terminal command

Response format - CHOOSE ONE:

1. For conversational requests (greetings, thanks, simple questions):
DIRECT_ANSWER: <your friendly response>

2. For tool-requiring requests:
THOUGHT: <your analysis>
ACTIONS: <tool calls in format tool_name("arg1", "arg2")>"""
        
        history_context = f"\nPrevious context: {context}" if context else ""
        prompt = f"""User request: {user_input}{history_context}

Analyze the request and decide: Does this require tools (code, files, web)? Or is it purely conversational?"""
        
        return self._call_llm(prompt, system_prompt)
    
    def _fallback_think(self, user_input: str) -> str:
        """Fallback when Ollama is not available - tries simple decision via LLM"""
        try:
            simple_system = """Analyze if this request is purely conversational or requires code/files.
If conversational (greeting, thanks, simple question), respond: DIRECT_ANSWER: <response>
If it needs work, respond: ACTIONS: """
            
            response = self._llm_manager.generate(user_input, simple_system, model=self.model)
            
            if response and "DIRECT_ANSWER:" in response:
                return response
            elif response and "ACTIONS:" not in response:
                return f"DIRECT_ANSWER: {response.strip()}"
        except:
            pass
        
        user_lower = user_input.lower()
        
        code = None
        filename = "output.py"
        
        if "fibonacci" in user_lower:
            code = self.FALLBACK_TEMPLATES["fibonacci"]
            filename = "fibonacci.py"
        elif "sort" in user_lower:
            code = self.FALLBACK_TEMPLATES["sort"]
            filename = "sort.py"
        else:
            code = self.FALLBACK_TEMPLATES["default"].format(request=user_input)
        
        tool_call = ToolCall(
            tool=ToolName.WRITE_FILE,
            arguments={"filename": filename, "content": code}
        )
        result = self._execute_tool(tool_call)
        tool_call.result = result
        tool_call.success = "Error" not in result
        
        self._fallback_tool_call = tool_call
        
        return f"""THOUGHT: The user wants code for: {user_input}. Creating Python file {filename}.
ACTIONS: write_file("{filename}", "...")"""
    
    def act(self, thought: str) -> List[ToolCall]:
        """Führe Aktionen basierend auf Thought aus."""
        # Check if we have a fallback tool call that was already executed
        if self._fallback_tool_call:
            tool_calls = [self._fallback_tool_call]
            self._fallback_tool_call = None  # Clear for next iteration
            return tool_calls
        
        tool_calls = self._parse_tool_calls(thought)
        
        for tc in tool_calls:
            result = self._execute_tool(tc)
            tc.result = result
            tc.success = "Error" not in result
        
        return tool_calls
    
    def observe(self, tool_calls: List[ToolCall]) -> str:
        """Beobachte Ergebnisse der Aktionen."""
        observations = []
        
        for tc in tool_calls:
            obs = f"[{tc.tool.value}] "
            if tc.success:
                obs += f"Success: {tc.result[:200] if tc.result else 'OK'}"
            else:
                obs += f"Failed: {tc.result}"
            observations.append(obs)
        
        return "\n".join(observations)
    
    def run(self, user_input: str) -> Tuple[str, List[TAOState]]:
        """Führe vollständige TAO-Loop aus."""
        self.history = []
        context = ""
        
        for i in range(1, self.max_iterations + 1):
            logger.info(f"TAO Iteration {i}/{self.max_iterations}")
            
            thought = self.think(user_input, context)
            
            if thought.startswith("DIRECT_ANSWER:"):
                direct_answer = thought[len("DIRECT_ANSWER:"):].strip()
                state = TAOState(
                    iteration=i,
                    thought=thought,
                    tool_calls=[],
                    observations=[]
                )
                state.final_result = direct_answer
                self.history.append(state)
                return direct_answer, self.history
            
            tool_calls = self.act(thought)
            observation = self.observe(tool_calls)
            
            state = TAOState(
                iteration=i,
                thought=thought,
                tool_calls=tool_calls,
                observations=[observation]
            )
            self.history.append(state)
            
            context = f"Iteration {i}: {observation}"
            
            if not tool_calls:
                if thought and "THOUGHT:" in thought:
                    state.final_result = thought
                    break
            elif all(tc.success for tc in tool_calls):
                state.final_result = observation
                break
        
        if self.history:
            last_state = self.history[-1]
            return last_state.final_result or observation, self.history
        
        return "No result", self.history


class ThoughtActionObservation:
    """Wrapper-Klasse für Kompatibilität mit agent.py"""
    
    def __init__(self):
        self.tao_loop = TAOLoop()
        self.think = self._think
        self.act = self._act
        self.observe = self._observe
    
    def _think(self, input_data: Any) -> str:
        """Think - ruft Ollama auf"""
        result, _ = self.tao_loop.run(str(input_data))
        return result
    
    def _act(self, thought: str) -> List[ToolCall]:
        """Act - führt Tools aus"""
        return self.tao_loop.act(thought)
    
    def _observe(self, action: Any) -> str:
        """Observe - sammelt Ergebnisse"""
        if isinstance(action, list):
            return self.tao_loop.observe(action)
        return str(action)


# Convenience function
def run_tao_loop(user_input: str) -> str:
    """Führe TAO-Loop aus und gebe Ergebnis zurück"""
    loop = TAOLoop()
    result, history = loop.run(user_input)
    return result


if __name__ == "__main__":
    loop = TAOLoop()
    print("Testing TAO Loop...")
    result, history = loop.run("schreibe eine Fibonacci Funktion")
    print(f"Result: {result}")
    print(f"Iterations: {len(history)}")
    
    if os.path.exists("fibonacci.py"):
        print("\n✓ fibonacci.py created!")
        with open("fibonacci.py", "r") as f:
            print(f"Content:\n{f.read()}")