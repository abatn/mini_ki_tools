from typing import Tuple, Optional, Dict
# Plugin Hooks System - OpenCode-kompatibles Plugin-System
# Ermöglicht tool.execute.before/after Hooks, session.idle Hooks

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HookType(Enum):
    """Types of hooks available"""
    TOOL_EXECUTE_BEFORE = "tool.execute.before"
    TOOL_EXECUTE_AFTER = "tool.execute.after"
    SESSION_IDLE = "session.idle"
    SESSION_START = "session.start"
    SESSION_STOP = "session.stop"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"


@dataclass
class HookContext:
    """Context passed to hooks"""
    session_id: str
    user_id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass  
class HookResult:
    """Result from hook execution"""
    allowed: bool = True
    modified_arguments: Optional[Dict[str, Any]] = None
    modified_result: Optional[Any] = None
    error_message: Optional[str] = None
    agent_result: Optional[Dict[str, Any]] = None  # For reactive subagent spawning
    stop_session: bool = False


HookFunc = Callable[[HookContext], Awaitable[HookResult]]


class Plugin:
    """Plugin with hooks"""
    
    def __init__(self, name: str, hooks: Dict[HookType, HookFunc] = None):
        self.name = name
        self.hooks = hooks or {}
        self.enabled = True
    
    def register_hook(self, hook_type: HookType, func: HookFunc):
        """Register a hook function"""
        self.hooks[hook_type] = func
    
    async def trigger(
        self, 
        hook_type: HookType, 
        context: HookContext
    ) -> Optional[HookResult]:
        """Trigger a hook"""
        if not self.enabled or hook_type not in self.hooks:
            return None
        
        try:
            result = await self.hooks[hook_type](context)
            logger.info(f"Plugin {self.name} hook {hook_type.value} triggered")
            return result
        except Exception as e:
            logger.error(f"Plugin {self.name} hook error: {e}")
            return HookResult(error_message=str(e))


class PluginManager:
    """Manages all plugins and their hooks"""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.hook_listeners: Dict[HookType, List[str]] = {
            hook_type: [] for hook_type in HookType
        }
    
    def register_plugin(self, plugin: Plugin):
        """Register a plugin"""
        self.plugins[plugin.name] = plugin
        
        for hook_type in plugin.hooks:
            if hook_type not in self.hook_listeners:
                self.hook_listeners[hook_type] = []
            if plugin.name not in self.hook_listeners[hook_type]:
                self.hook_listeners[hook_type].append(plugin.name)
        
        logger.info(f"Plugin registered: {plugin.name}")
    
    def unregister_plugin(self, name: str):
        """Unregister a plugin"""
        if name in self.plugins:
            plugin = self.plugins[name]
            for hook_type in plugin.hooks:
                if hook_type in self.hook_listeners:
                    self.hook_listeners[hook_type].remove(name)
            del self.plugins[name]
            logger.info(f"Plugin unregistered: {name}")
    
    async def trigger(
        self,
        hook_type: HookType,
        context: HookContext
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Trigger all hooks for a given type.
        
        Returns:
            Tuple of (allowed, modified_args, error_message)
        """
        allowed = True
        modified_args = context.arguments.copy() if context.arguments else {}
        error_message = None
        agent_result = None
        
        listeners = self.hook_listeners.get(hook_type, [])
        
        for plugin_name in listeners:
            plugin = self.plugins.get(plugin_name)
            if not plugin:
                continue
            
            result = await plugin.trigger(hook_type, context)
            
            if result:
                if not result.allowed:
                    allowed = False
                    error_message = result.error_message or "Blocked by plugin"
                    break
                
                if result.modified_arguments:
                    modified_args = result.modified_arguments
                
                if result.agent_result:
                    agent_result = result.agent_result
                
                if result.stop_session:
                    context.metadata["stop_session"] = True
        
        return allowed, modified_args if modified_args != context.arguments else None, error_message
    
    def get_plugins(self) -> List[Dict]:
        """Get list of registered plugins"""
        return [
            {
                "name": p.name,
                "hooks": [h.value for h in p.hooks.keys()],
                "enabled": p.enabled
            }
            for p in self.plugins.values()
        ]


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


# Example hooks for demonstration
async def example_tool_execute_before(context: HookContext) -> HookResult:
    """Example: Block write_file to certain paths"""
    if context.tool_name == "write_file":
        path = context.arguments.get("filename", "")
        if path.startswith("/etc") or path.startswith("/root"):
            return HookResult(
                allowed=False,
                error_message=f"Cannot write to blocked path: {path}"
            )
    
    return HookResult(allowed=True)


async def example_tool_execute_after(context: HookContext) -> HookResult:
    """Example: Log tool executions"""
    logger.info(
        f"Tool {context.tool_name} executed by {context.user_id}: "
        f"success={context.success}"
    )
    return HookResult(allowed=True)


async def example_session_idle(context: HookContext) -> HookResult:
    """Example: Auto-save on idle"""
    logger.info(f"Session {context.session_id} idle")
    return HookResult(allowed=True)


# Initialize default hooks
def initialize_default_hooks():
    """Initialize with example hooks"""
    manager = get_plugin_manager()
    
    plugin = Plugin(
        "default_hooks",
        {
            HookType.TOOL_EXECUTE_BEFORE: example_tool_execute_before,
            HookType.TOOL_EXECUTE_AFTER: example_tool_execute_after,
            HookType.SESSION_IDLE: example_session_idle
        }
    )
    
    manager.register_plugin(plugin)


from typing import Tuple