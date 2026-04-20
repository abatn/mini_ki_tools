# Agent Permissions System - OpenCode-kompatibles Berechtigungssystem
# Granulare Kontrolle darüber, welche Agents welche Tools verwenden dürfen

import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PermissionAction(Enum):
    """Possible permission actions"""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionRule:
    """Single permission rule"""
    tool_pattern: str  # glob pattern, e.g., "file_*", "git.*"
    action: PermissionAction
    description: str = ""
    conditions: Dict = field(default_factory=dict)


@dataclass
class AgentPermissions:
    """Permissions for an agent"""
    agent_name: str
    tools: List[PermissionRule] = field(default_factory=list)
    max_file_size_mb: int = 10
    allow_subagent: bool = True
    allowed_directories: List[str] = field(default_factory=list)
    denied_directories: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    max_iterations: int = 10
    task_budget: int = -1  # -1 = unlimited, 0 = no subagents, N = N subagent calls


@dataclass
class PermissionCheckResult:
    """Result of permission check"""
    allowed: bool
    action: PermissionAction
    reason: str = ""
    modified_args: Dict = field(default_factory=dict)


class PermissionStore:
    """Store for agent permissions"""
    
    def __init__(self):
        self.permissions: Dict[str, AgentPermissions] = {}
        self._default_permissions: Optional[AgentPermissions] = None
        self._load_default()
    
    def _load_default(self):
        """Load default permissions"""
        self._default_permissions = AgentPermissions(
            agent_name="default",
            tools=[
                PermissionRule("file_*", PermissionAction.ALLOW, "File operations"),
                PermissionRule("git.*", PermissionAction.ALLOW, "Git operations"),
                PermissionRule("search", PermissionAction.ALLOW, "Search"),
                PermissionRule("execute_code", PermissionAction.ALLOW, "Execute code"),
                PermissionRule("run_command", PermissionAction.ALLOW, "Run commands"),
            ],
            max_file_size_mb=10,
            allow_subagent=True,
            max_iterations=10,
            task_budget=10
        )
        self.permissions["default"] = self._default_permissions
    
    def set_permissions(self, agent_name: str, perms: AgentPermissions):
        """Set permissions for an agent"""
        self.permissions[agent_name] = perms
        logger.info(f"Permissions set for agent: {agent_name}")
    
    def get_permissions(self, agent_name: str) -> AgentPermissions:
        """Get permissions for an agent"""
        return self.permissions.get(agent_name, self._default_permissions)
    
    def check_tool(self, agent_name: str, tool_name: str) -> PermissionCheckResult:
        """Check if agent can use a tool"""
        perms = self.get_permissions(agent_name)
        
        for rule in perms.tools:
            if self._match_pattern(tool_name, rule.tool_pattern):
                return PermissionCheckResult(
                    allowed=rule.action == PermissionAction.ALLOW,
                    action=rule.action,
                    reason=rule.description
                )
        
        # Default: deny
        return PermissionCheckResult(
            allowed=False,
            action=PermissionAction.DENY,
            reason="No matching rule"
        )
    
    def check_directory(self, agent_name: str, path: str) -> bool:
        """Check if agent can access a directory"""
        perms = self.get_permissions(agent_name)
        
        # Check denials first
        for denied in perms.denied_directories:
            if path.startswith(denied) or self._match_pattern(path, denied):
                return False
        
        # Check allowed list
        if perms.allowed_directories:
            for allowed in perms.allowed_directories:
                if path.startswith(allowed) or self._match_pattern(path, allowed):
                    return True
            return False
        
        return True
    
    def check_subagent(self, agent_name: str, target_agent: str = None) -> bool:
        """Check if agent can spawn subagents"""
        perms = self.get_permissions(agent_name)
        
        if not perms.allow_subagent:
            return False
        
        if perms.task_budget == 0:
            return False
        
        return True
    
    def use_task_budget(self, agent_name: str) -> bool:
        """Use one task budget from agent"""
        perms = self.get_permissions(agent_name)
        
        if perms.task_budget == -1:  # unlimited
            return True
        
        if perms.task_budget > 0:
            perms.task_budget -= 1
            return True
        
        return False
    
    def get_remaining_budget(self, agent_name: str) -> int:
        """Get remaining task budget"""
        perms = self.get_permissions(agent_name)
        return perms.task_budget
    
    def _match_pattern(self, tool_name: str, pattern: str) -> bool:
        """Match tool name against pattern"""
        import fnmatch
        return fnmatch.fnmatch(tool_name.lower(), pattern.lower())
    
    def to_dict(self) -> Dict:
        """Export permissions as dict"""
        return {
            agent_name: {
                "tools": [
                    {
                        "pattern": r.tool_pattern,
                        "action": r.action.value,
                        "description": r.description
                    }
                    for r in p.tools
                ],
                "max_file_size_mb": p.max_file_size_mb,
                "allow_subagent": p.allow_subagent,
                "task_budget": p.task_budget
            }
            for agent_name, p in self.permissions.items()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PermissionStore":
        """Import permissions from dict"""
        store = cls()
        store.permissions = {}
        
        for agent_name, perms_data in data.items():
            tools = [
                PermissionRule(
                    tool_pattern=t["pattern"],
                    action=PermissionAction(t["action"]),
                    description=t.get("description", "")
                )
                for t in perms_data.get("tools", [])
            ]
            
            store.permissions[agent_name] = AgentPermissions(
                agent_name=agent_name,
                tools=tools,
                max_file_size_mb=perms_data.get("max_file_size_mb", 10),
                allow_subagent=perms_data.get("allow_subagent", True),
                task_budget=perms_data.get("task_budget", 10)
            )
        
        return store


# Global permission store
_permission_store: Optional[PermissionStore] = None


def get_permission_store() -> PermissionStore:
    """Get global permission store"""
    global _permission_store
    if _permission_store is None:
        _permission_store = PermissionStore()
    return _permission_store


def check_tool_permission(agent_name: str, tool_name: str) -> bool:
    """Quick check if tool is allowed"""
    store = get_permission_store()
    result = store.check_tool(agent_name, tool_name)
    return result.allowed


def check_directory_permission(agent_name: str, path: str) -> bool:
    """Quick check if directory is allowed"""
    store = get_permission_store()
    return store.check_directory(agent_name, path)


def can_spawn_subagent(agent_name: str) -> bool:
    """Quick check if can spawn subagent"""
    store = get_permission_store()
    return store.check_subagent(agent_name)


def use_task_budget(agent_name: str) -> bool:
    """Use one task budget"""
    store = get_permission_store()
    return store.use_task_budget(agent_name)


# Default permission configurations for built-in agents
BUILT_IN_AGENT_PERMISSIONS = {
    "build": {
        "tools": [
            {"pattern": "file_*", "action": "allow"},
            {"pattern": "git.*", "action": "allow"},
            {"pattern": "search", "action": "allow"},
            {"pattern": "execute_code", "action": "allow"},
            {"pattern": "run_command", "action": "allow"},
        ],
        "task_budget": 10
    },
    "architect": {
        "tools": [
            {"pattern": "file_read", "action": "allow"},
            {"pattern": "search", "action": "allow"},
            {"pattern": "execute_code", "action": "deny"},
        ],
        "task_budget": 5
    },
    "review": {
        "tools": [
            {"pattern": "file_read", "action": "allow"},
            {"pattern": "git.*", "action": "allow"},
            {"pattern": "search", "action": "allow"},
            {"pattern": "write_file", "action": "deny"},
        ],
        "task_budget": 0
    }
}


def initialize_default_permissions():
    """Initialize with built-in agent permissions"""
    store = get_permission_store()
    
    for agent_name, perms_data in BUILT_IN_AGENT_PERMISSIONS.items():
        tools = [
            PermissionRule(
                tool_pattern=t["pattern"],
                action=PermissionAction(t["action"])
            )
            for t in perms_data.get("tools", [])
        ]
        
        agent_perms = AgentPermissions(
            agent_name=agent_name,
            tools=tools,
            task_budget=perms_data.get("task_budget", 10)
        )
        
        store.set_permissions(agent_name, agent_perms)


def load_permissions_from_config(config_path: str):
    """Load permissions from config file"""
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        store = PermissionStore.from_dict(data)
        global _permission_store
        _permission_store = store
        logger.info(f"Permissions loaded from {config_path}")
    except Exception as e:
        logger.error(f"Failed to load permissions: {e}")


def save_permissions_to_config(config_path: str):
    """Save permissions to config file"""
    try:
        store = get_permission_store()
        data = store.to_dict()
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Permissions saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save permissions: {e}")