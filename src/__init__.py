# mini_ki_tools - AI Agent System
__version__ = "1.0.0"

# LLM Provider
from .llm_provider import (
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    AnthropicProvider,
    OpenRouterProvider,
    LLMProviderFactory,
    LLMProviderManager,
    get_llm_manager,
    get_llm_provider,
    generate
)

# Core Agent
from .agent import Agent
from .thought_action_observation import TAOLoop, ThoughtActionObservation, run_tao_loop
from .tree_of_thoughts import TreeOfThoughts, AgentWithToT

# Tools & Integration
from .tools import ToolRegistry
from .git_integration import GitIntegration

# Memory & Processing
from .long_term_memory import store_memory, search_memory, delete_memory, get_memory_stats, get_all_memory
from .batch_processor import BatchProcessor

# Collaboration & Config
from .collaboration import CollaborationRoom, CollaborationManager, handle_collab_connection, collaboration_manager
from .config_exporter import ConfigExporter, ConfigImporter, handle_export_command, handle_import_command

# Sandbox & Security
from .sandbox_manager import SandboxManager, get_sandbox_manager, execute_in_sandbox
from .audit_logger import AuditLogger, get_audit_logger, log_action

# Orchestration & Self-Healing
from .orchestrator import Orchestrator, OrchestratorAgent, AgentRole, SubAgent
from .self_healing import SelfHealingEngine, SelfHealingAgent

# MCP & Marketplace
from .mcp_marketplace import MCPMarketplace
from .mcp_client import MCPClient

# Subagents
from .subagents import NativeSubAgents, MultiAgentOrchestrator, SubAgentType

# Utilities
from .context import ProjectContext
from .debugger import Debugger
from .undo_manager import UndoManager
from .plugin_manager import PluginManager
from .code_refactoring_engine import CodeRefactoringEngine
from .code_review import CodeReviewAgent
from .dependency_installer import install_packages, safe_import
from .embedding import EmbeddingModel, get_embedding
from .inline_completions import InlineCompletionProvider
from .security_scanner import SecurityScanner
from .scheduler import add_job, list_jobs, remove_job
from .voice_interface import VoiceInterface
from .utils import setup_directories, load_config, save_config
from .cli import HeadlessAgent, CLI

# OpenCode-like Features
from .plugin_hooks import (
    Plugin, PluginManager, HookType, HookContext, HookResult,
    get_plugin_manager
)
from .agent_permissions import (
    AgentPermissions, PermissionStore, check_tool_permission,
    check_directory_permission, can_spawn_subagent, use_task_budget,
    get_permission_store, initialize_default_permissions
)
from .slash_commands import (
    SlashCommand, CommandRegistry, CommandContext, CommandResult,
    get_command_registry, is_command, get_help_text
)
from .team_management import (
    Team, Teammate, TeamMessage, TeamManager,
    get_team_manager, get_team_tools
)

# Provider Manager
from .provider_manager import (
    ProviderManager,
    get_provider_manager,
    get_available_providers,
    get_best_llm_config
)

# Reasoning Engine
from .reasoning_engine import (
    ReasoningEngine,
    get_reasoning_engine,
    ReasoningMode
)

# Workspace
from .workspace import (
    WorkspaceManager,
    get_workspace_manager,
    get_workspace_path,
    validate_path
)