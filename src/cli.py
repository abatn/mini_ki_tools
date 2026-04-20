# CLI / Headless Mode for Agent
# Agent läuft ohne Web-UI, gibt Ergebnisse als JSON/Text aus. Perfekt für CI/CD Pipelines.

import argparse
import json
import sys
import os
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from .agent import Agent
except ImportError:
    class Agent:
        pass
from tools import ToolRegistry
from long_term_memory import store_memory, search_memory


class HeadlessAgent:
    """
    Headless Agent für CLI / CI/CD.
    Agent läuft ohne Web-UI, gibt Ergebnisse als JSON/Text aus.
    """
    
    def __init__(
        self,
        model: str = "llama3.2",
        output_format: str = "text",
        verbose: bool = False
    ):
        self.model = model
        self.output_format = output_format
        self.verbose = verbose
        self.agent = Agent()
        self.tool_registry = ToolRegistry()
    
    def _log(self, message: str):
        """Log message if verbose mode"""
        if self.verbose:
            print(f"[DEBUG] {message}", file=sys.stderr)
    
    def execute_task(self, task: str) -> Dict[str, Any]:
        """
        Führe Task im Headless-Mode aus.
        
        Args:
            task: Die auszuführende Aufgabe
            
        Returns:
            Dict mit Ergebnis
        """
        self._log(f"Executing task: {task}")
        
        try:
            # Execute via agent
            result = self.agent.process_message(task)
            
            return {
                "success": True,
                "task": task,
                "result": result,
                "model": self.model
            }
            
        except Exception as e:
            self._log(f"Error: {e}")
            return {
                "success": False,
                "task": task,
                "error": str(e),
                "model": self.model
            }
    
    def execute_with_tools(self, task: str, tools: List[str]) -> Dict[str, Any]:
        """
        Führe Task mit spezifischen Tools aus.
        
        Args:
            task: Die auszuführende Aufgabe
            tools: Liste von Tool-Namen
            
        Returns:
            Dict mit Ergebnis
        """
        self._log(f"Executing task with tools: {tools}")
        
        try:
            # Get available tools
            available_tools = self.tool_registry.list_tools()
            
            # Filter requested tools
            selected_tools = [t for t in available_tools if t['name'] in tools]
            
            # Execute with tools
            result = self.agent.process_message(task)
            
            return {
                "success": True,
                "task": task,
                "tools_used": tools,
                "result": result,
                "model": self.model
            }
            
        except Exception as e:
            return {
                "success": False,
                "task": task,
                "error": str(e),
                "tools": tools
            }
    
    def output_result(self, result: Dict[str, Any]):
        """
        Ausgabe des Ergebnisses im gewünschten Format.
        
        Args:
            result: Das Ergebnis-Dict
        """
        if self.output_format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif self.output_format == "jsonl":
            print(json.dumps(result, ensure_ascii=False))
        else:
            # Text format
            if result.get("success"):
                print(result.get("result", ""))
            else:
                print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
                sys.exit(1)


class CLI:
    """
    Command Line Interface für den Agent.
    Unterstützt --headless, --task "Beschreibung", --output json.
    """
    
    def __init__(self):
        self.parser = self._build_parser()
    
    def _build_parser(self) -> argparse.ArgumentParser:
        """Build argument parser"""
        parser = argparse.ArgumentParser(
            description="Mini KI Tools - CLI / Headless Mode",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python -m src.cli --task "Hello, how are you?"
  python -m src.cli --headless --task "List files in current directory"
  python -m src.cli --task "Analyze code" --output json
  python -m src.cli --task "Run tests" --model gpt-4o --verbose
  python -m src.cli --interactive
            """
        )
        
        # Main options
        parser.add_argument(
            "--task", "-t",
            type=str,
            help="Task description to execute"
        )
        
        parser.add_argument(
            "--headless", "-H",
            action="store_true",
            help="Run in headless mode (no interactive prompts)"
        )
        
        parser.add_argument(
            "--output", "-o",
            type=str,
            choices=["text", "json", "jsonl"],
            default="text",
            help="Output format (default: text)"
        )
        
        parser.add_argument(
            "--model", "-m",
            type=str,
            default="llama3.2",
            help="Model to use (default: llama3.2)"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )
        
        # Interactive mode
        parser.add_argument(
            "--interactive", "-i",
            action="store_true",
            help="Start interactive CLI mode"
        )
        
        # Tools
        parser.add_argument(
            "--tools", "-T",
            type=str,
            nargs="+",
            help="Specific tools to use"
        )
        
        # Memory
        parser.add_argument(
            "--memory",
            type=str,
            help="Store result in long-term memory"
        )
        
        parser.add_argument(
            "--search-memory",
            type=str,
            help="Search long-term memory"
        )
        
        # File input/output
        parser.add_argument(
            "--input-file", "-f",
            type=str,
            help="Read task from file"
        )
        
        parser.add_argument(
            "--output-file", "-O",
            type=str,
            help="Write output to file"
        )
        
        return parser
    
    def run(self, args: List[str] = None):
        """Run CLI with arguments"""
        parsed = self.parser.parse_args(args)
        
        # Create headless agent
        agent = HeadlessAgent(
            model=parsed.model,
            output_format=parsed.output,
            verbose=parsed.verbose
        )
        
        # Handle interactive mode
        if parsed.interactive:
            self._run_interactive(agent)
            return
        
        # Get task from file or argument
        task = parsed.task
        
        if parsed.input_file:
            try:
                task = Path(parsed.input_file).read_text().strip()
            except Exception as e:
                print(f"Error reading input file: {e}", file=sys.stderr)
                sys.exit(1)
        
        if not task:
            print("Error: No task specified. Use --task or --input-file", file=sys.stderr)
            sys.exit(1)
        
        # Execute task
        if parsed.tools:
            result = agent.execute_with_tools(task, parsed.tools)
        else:
            result = agent.execute_task(task)
        
        # Handle memory
        if parsed.memory:
            try:
                store_memory(
                    content=parsed.memory,
                    metadata={"task": task, "result": str(result)}
                )
            except Exception as e:
                agent._log(f"Memory store error: {e}")
        
        if parsed.search_memory:
            try:
                memories = search_memory(parsed.search_memory)
                result["memories"] = memories
            except Exception as e:
                agent._log(f"Memory search error: {e}")
        
        # Output result
        if parsed.output_file:
            try:
                Path(parsed.output_file).write_text(
                    json.dumps(result, indent=2) if parsed.output == "json" 
                    else result.get("result", "")
                )
            except Exception as e:
                print(f"Error writing output file: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            agent.output_result(result)
    
    def _run_interactive(self, agent: HeadlessAgent):
        """Run interactive CLI mode"""
        print("Mini KI Tools - Interactive Mode")
        print("Type 'exit' or 'quit' to exit")
        print("Type 'help' for available commands")
        print("-" * 40)
        
        while True:
            try:
                task = input("\n> ").strip()
                
                if task in ["exit", "quit"]:
                    print("Goodbye!")
                    break
                
                if task in ["help", "?"]:
                    print("""
Available commands:
  exit, quit - Exit interactive mode
  help, ?    - Show this help
  tools      - List available tools
  memory     - Search memory
  clear      - Clear screen
  <any>      - Execute as task
                    """)
                    continue
                
                if task == "tools":
                    tools = agent.tool_registry.list_tools()
                    print(f"Available tools: {len(tools)}")
                    for t in tools:
                        print(f"  - {t['name']}: {t.get('description', '')}")
                    continue
                
                if task == "clear":
                    os.system("clear" if os.name == "posix" else "cls")
                    continue
                
                if task.startswith("memory "):
                    query = task[7:]
                    try:
                        results = search_memory(query)
                        print(f"Found {len(results)} memories:")
                        for r in results:
                            print(f"  - {r.get('text', '')[:100]}")
                    except Exception as e:
                        print(f"Error: {e}")
                    continue
                
                if not task:
                    continue
                
                # Execute task
                result = agent.execute_task(task)
                agent.output_result(result)
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)


# Main entry point
def main():
    """Main entry point for CLI"""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()