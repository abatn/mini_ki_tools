# Slash Commands System - OpenCode-kompatible Befehle
# Ermöglicht /command syntax wie /workflow, /test, /make, etc.

import re
import shlex
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Context for command execution"""
    user_id: str
    session_id: str
    workspace_path: str
    agent_name: str
    arguments: Dict[str, Any]
    raw_input: str


class CommandResult:
    """Result from command execution"""
    def __init__(
        self,
        success: bool,
        output: str = "",
        agent_name: str = None,
        continue_session: bool = True,
        metadata: Dict = None
    ):
        self.success = success
        self.output = output
        self.agent_name = agent_name
        self.continue_session = continue_session
        self.metadata = metadata or {}


CommandFunc = Callable[[CommandContext], Awaitable[CommandResult]]


class SlashCommand:
    """A slash command"""
    
    def __init__(
        self,
        name: str,
        description: str,
        func: CommandFunc,
        aliases: List[str] = None,
        requires_agent: bool = True,
        hidden: bool = False
    ):
        self.name = name
        self.description = description
        self.func = func
        self.aliases = aliases or []
        self.requires_agent = requires_agent
        self.hidden = hidden
    
    def matches(self, input_str: str) -> bool:
        """Check if input matches this command"""
        input_lower = input_str.lower().strip()
        
        if input_lower.startswith(f"/{self.name}"):
            return True
        
        for alias in self.aliases:
            if input_lower.startswith(f"/{alias}"):
                return True
        
        return False


class CommandRegistry:
    """Registry for all slash commands"""
    
    def __init__(self):
        self.commands: Dict[str, SlashCommand] = {}
        self._register_default_commands()
    
    def _register_default_commands(self):
        """Register default commands"""
        from slash_commands_impl import (
            cmd_workflow, cmd_test, cmd_make, cmd_explain,
            cmd_bug, cmd_refactor, cmd_review, cmd_share
        )
        
        self.register(cmd_workflow)
        self.register(cmd_test)
        self.register(cmd_make)
        self.register(cmd_explain)
        self.register(cmd_bug)
        self.register(cmd_refactor)
        self.register(cmd_review)
        self.register(cmd_share)
    
    def register(self, command: SlashCommand):
        """Register a command"""
        self.commands[command.name] = command
        for alias in command.aliases:
            self.commands[alias] = command
        logger.info(f"Command registered: /{command.name}")
    
    def unregister(self, name: str):
        """Unregister a command"""
        if name in self.commands:
            command = self.commands[name]
            del self.commands[name]
            for alias in command.aliases:
                if alias in self.commands:
                    del self.commands[alias]
    
    def parse(self, input_str: str) -> Optional[tuple]:
        """
        Parse input into command and arguments.
        
        Returns:
            Tuple of (command, args_string) or None
        """
        input_str = input_str.strip()
        
        if not input_str.startswith("/"):
            return None
        
        # Extract command
        match = re.match(r"/(\w+)(?:\s+(.*))?", input_str)
        if not match:
            return None
        
        command_name = match.group(1).lower()
        args_string = match.group(2) or ""
        
        return command_name, args_string
    
    async def execute(
        self,
        input_str: str,
        context: CommandContext
    ) -> Optional[CommandResult]:
        """Execute a command from input string"""
        parsed = self.parse(input_str)
        
        if not parsed:
            return None
        
        command_name, args_string = parsed
        
        # Find command
        command = self.commands.get(command_name)
        
        if not command:
            return CommandResult(
                success=False,
                output=f"Unknown command: /{command_name}"
            )
        
        # Parse arguments
        try:
            args = shlex.split(args_string) if args_string else []
        except ValueError:
            args = args_string.split()
        
        # Build context
        context.arguments = self._parse_args(args)
        context.raw_input = input_str
        
        # Execute
        try:
            result = await command.func(context)
            return result
        except Exception as e:
            logger.error(f"Command error: {e}")
            return CommandResult(
                success=False,
                output=f"Error: {str(e)}"
            )
    
    def _parse_args(self, args: List[str]) -> Dict[str, Any]:
        """Parse argument list into dict"""
        result = {}
        key = None
        
        for arg in args:
            if arg.startswith("--") or arg.startswith("-"):
                key = arg.lstrip("-")
                result[key] = True
            elif key:
                result[key] = arg
                key = None
            else:
                result[f"arg{len(result)}"] = arg
        
        return result
    
    def get_command_list(self) -> List[Dict]:
        """Get list of all commands"""
        seen = set()
        commands = []
        
        for cmd in self.commands.values():
            if cmd.name in seen:
                continue
            seen.add(cmd.name)
            
            commands.append({
                "name": f"/{cmd.name}",
                "description": cmd.description,
                "aliases": [f"/{a}" for a in cmd.aliases],
                "hidden": cmd.hidden
            })
        
        return commands


# Global command registry
_command_registry: Optional[CommandRegistry] = None


def get_command_registry() -> CommandRegistry:
    """Get global command registry"""
    global _command_registry
    if _command_registry is None:
        _command_registry = CommandRegistry()
    return _command_registry


async def execute_command(
    input_str: str,
    user_id: str = "default",
    session_id: str = "default",
    workspace_path: str = "/workspace",
    agent_name: str = "build"
) -> Optional[CommandResult]:
    """Execute a slash command from input string"""
    registry = get_command_registry()
    
    context = CommandContext(
        user_id=user_id,
        session_id=session_id,
        workspace_path=workspace_path,
        agent_name=agent_name,
        arguments={},
        raw_input=input_str
    )
    
    return await registry.execute(input_str, context)


def is_command(input_str: str) -> bool:
    """Check if input is a slash command"""
    return input_str.strip().startswith("/")


def get_help_text() -> str:
    """Get help text for all commands"""
    registry = get_command_registry()
    commands = registry.get_command_list()
    
    lines = ["Available commands:"]
    for cmd in commands:
        if cmd["hidden"]:
            continue
        lines.append(f"  {cmd['name']} - {cmd['description']}")
    
    return "\n".join(lines)