"""
Mini KI Tools - Python Extension Host Bridge
This module provides the interface between VS Code extension and bundled Python environment.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import core modules
try:
    from agent import Agent
    from llm_provider import get_llm_manager, LLMProvider
    from thought_action_observation import TAOLoop
    from tools import ToolRegistry
    from git_integration import GitIntegration
    from long_term_memory import store_memory, search_memory
    from batch_processor import BatchProcessor
    from scheduler import scheduler
    from orchestrator import Orchestrator
    from self_healing import SelfHealingEngine
    from subagents import BaseSubAgent
    from mcp_client import MCPClient
    from sandbox_manager import SandboxManager
    from audit_logger import AuditLogger
    from voice_interface import VoiceInterface
    from code_review import CodeReviewAgent
    from code_refactoring_engine import CodeRefactoringEngine
    from tree_of_thoughts import TreeOfThoughts
    from config_exporter import ConfigExporter
    from collaboration import CollaborationManager
    from plugin_manager import PluginManager
    from embedding import get_embedding
    from inline_completions import InlineCompletionProvider
    from security_scanner import SecurityScanner
    from undo_manager import UndoManager
    from utils import load_config, save_config
    from cli import HeadlessAgent
    MODULES_LOADED = True
except ImportError as e:
    logger.warning(f"Some modules could not be loaded: {e}")
    MODULES_LOADED = False


class ExtensionHostBridge:
    """
    Bridge between VS Code extension and Python agent.
    Runs directly in VS Code's extension host process.
    """
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or os.getcwd()
        self.agent = None
        self.tool_registry = None
        self.llm_provider = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the agent and all components"""
        if not MODULES_LOADED:
            logger.error("Core modules not loaded - check Python environment")
            return
        
        # Get LLM configuration from environment
        llm_url = os.environ.get("LLM_URL", "http://localhost:11434")
        llm_model = os.environ.get("LLM_MODEL", "llama3.2")
        llm_provider_type = os.environ.get("LLM_PROVIDER", "ollama")
        
        logger.info(f"Initializing with LLM: {llm_provider_type}/{llm_model} at {llm_url}")
        
        # Initialize LLM provider - use get_llm_manager() without args, it reads from env
        self.llm_provider = get_llm_manager()
        
        # Initialize agent
        self.agent = Agent()
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        
        logger.info("Extension host bridge initialized")
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """Process a chat message and return result"""
        if not self.agent:
            return {"error": "Agent not initialized", "success": False}
        
        try:
            result = self.agent.process_message(message)
            return {
                "success": True,
                "result": result,
                "workspace": self.workspace_path
            }
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {"error": str(e), "success": False}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent"""
        return {
            "connected": self.agent is not None,
            "workspace": self.workspace_path,
            "llm": {
                "provider": os.environ.get("LLM_PROVIDER", "ollama"),
                "model": os.environ.get("LLM_MODEL", "llama3.2"),
                "url": os.environ.get("LLM_URL", "http://localhost:11434")
            },
            "modules_loaded": MODULES_LOADED
        }
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool"""
        if not self.tool_registry:
            return {"error": "Tool registry not initialized", "success": False}
        
        try:
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                return {"error": f"Tool {tool_name} not found", "success": False}
            
            result = tool.execute(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return {"error": str(e), "success": False}
    
    def read_file(self, filepath: str) -> Dict[str, Any]:
        """Read a file from workspace"""
        try:
            full_path = os.path.join(self.workspace_path, filepath)
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"success": True, "content": content, "path": full_path}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def write_file(self, filepath: str, content: str) -> Dict[str, Any]:
        """Write content to a file in workspace"""
        try:
            full_path = os.path.join(self.workspace_path, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True, "path": full_path}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def analyze_code(self, filepath: str) -> Dict[str, Any]:
        """Analyze code in a file"""
        try:
            result = self.read_file(filepath)
            if not result.get("success"):
                return result
            
            content = result["content"]
            # Use LLM to analyze code
            if self.llm_provider:
                analysis = self.llm_provider.generate(
                    prompt=f"Analyze this code and provide feedback:\n\n{content[:2000]}",
                    system_prompt="You are a code analysis expert. Provide concise, actionable feedback."
                )
                return {"success": True, "analysis": analysis, "file": filepath}
            return {"error": "LLM provider not available", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def refactor_code(self, filepath: str, instructions: str) -> Dict[str, Any]:
        """Refactor code based on instructions"""
        try:
            result = self.read_file(filepath)
            if not result.get("success"):
                return result
            
            content = result["content"]
            # Use LLM to refactor code
            if self.llm_provider:
                refactored = self.llm_provider.generate(
                    prompt=f"Refactor this code according to: {instructions}\n\nOriginal code:\n{content[:2000]}",
                    system_prompt="You are a code refactoring expert. Provide improved code that maintains the same functionality."
                )
                return {"success": True, "refactored": refactored, "file": filepath}
            return {"error": "LLM provider not available", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}


# Global bridge instance
_bridge = None

def get_bridge(workspace_path: str = None) -> ExtensionHostBridge:
    """Get or create the global bridge instance"""
    global _bridge
    if _bridge is None:
        _bridge = ExtensionHostBridge(workspace_path)
    return _bridge


def handle_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming message from VS Code extension"""
    command = message.get("command")
    params = message.get("params", {})
    
    bridge = get_bridge(params.get("workspace"))
    
    if command == "chat":
        return bridge.process_message(params.get("message", ""))
    elif command == "status":
        return bridge.get_status()
    elif command == "read":
        return bridge.read_file(params.get("filepath"))
    elif command == "write":
        return bridge.write_file(params.get("filepath"), params.get("content"))
    elif command == "analyze":
        return bridge.analyze_code(params.get("filepath"))
    elif command == "refactor":
        return bridge.refactor_code(params.get("filepath"), params.get("instructions"))
    elif command == "tool":
        return bridge.execute_tool(params.get("tool"), **params.get("kwargs", {}))
    else:
        return {"error": f"Unknown command: {command}", "success": False}


# CLI entry point for testing
if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Mini KI Tools Extension Host")
    parser.add_argument("--workspace", default=".", help="Workspace path")
    parser.add_argument("--command", help="Command to execute")
    parser.add_argument("--message", help="Message for chat command")
    parser.add_argument("--stdin", action="store_true", help="Read commands from stdin")
    
    args = parser.parse_args()
    
    if args.stdin:
        # Interactive mode: read JSON messages from stdin, write JSON to stdout
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
                result = handle_message(message)
                print(json.dumps(result), flush=True)
            except json.JSONDecodeError as e:
                print(json.dumps({"error": f"Invalid JSON: {e}"}), flush=True)
            except Exception as e:
                print(json.dumps({"error": str(e)}), flush=True)
    else:
        # Single command mode
        bridge = ExtensionHostBridge(args.workspace)
        
        if args.command:
            result = handle_message({
                "command": args.command,
                "params": {"message": args.message, "workspace": args.workspace}
            })
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(bridge.get_status(), indent=2))