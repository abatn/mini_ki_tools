# Workspace Path Manager
# Verwaltet den Workspace-Pfad für den Agenten mit Lese-, Schreib- und Ausführungsrechten

import os
import logging
from pathlib import Path
from typing import Optional, List
import yaml
import fnmatch

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Zentrale Verwaltung des Workspace-Pfades"""
    
    DEFAULT_CONFIG_PATH = "config/workspace.yaml"
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.environ.get(
            "WORKSPACE_CONFIG_PATH",
            self.DEFAULT_CONFIG_PATH
        )
        self._config = self._load_config()
        self._workspace_path = self._resolve_workspace_path()
    
    def _load_config(self) -> dict:
        """Lade Konfiguration aus YAML-Datei"""
        config = {
            "workspace_path": "/workspace",
            "read_only": False,
            "allowed_extensions": [".py", ".js", ".sh", ".txt", ".json", ".yaml", ".yml", ".md"],
            "blocked_paths": ["/etc", "/root", "/home/*/.ssh", "/home/*/.aws"],
            "max_file_size": 10,  # MB
            "execution_timeout": 30  # seconds
        }
        
        # Load from config file if exists
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                    config.update(file_config)
            except Exception as e:
                logger.warning(f"Failed to load workspace config: {e}")
        
        # Override with environment variable
        env_workspace = os.environ.get("WORKSPACE_PATH")
        if env_workspace:
            config["workspace_path"] = env_workspace
        
        return config
    
    def _resolve_workspace_path(self) -> str:
        """Löse den Workspace-Pfad auf"""
        path = self._config.get("workspace_path", "/workspace")
        
        # Resolve to absolute path
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        
        # Create directory if not exists
        os.makedirs(path, exist_ok=True)
        
        logger.info(f"Workspace path resolved to: {path}")
        return path
    
    def get_workspace_path(self) -> str:
        """Gib den Workspace-Pfad zurück"""
        return self._workspace_path
    
    def is_within_workspace(self, file_path: str) -> bool:
        """Prüfe ob ein Pfad innerhalb des Workspaces liegt"""
        try:
            # Resolve to absolute path
            abs_path = os.path.abspath(os.path.expanduser(file_path))
            workspace_abs = os.path.abspath(self._workspace_path)
            
            # Check if path is within workspace
            return abs_path.startswith(workspace_abs + os.sep) or abs_path == workspace_abs
        except Exception as e:
            logger.error(f"Error checking workspace path: {e}")
            return False
    
    def validate_path(self, file_path: str) -> tuple[bool, str]:
        """
        Validiere einen Pfad gegen die Workspace-Regeln.
        Returns: (is_valid, error_message)
        """
        try:
            abs_path = os.path.abspath(os.path.expanduser(file_path))
            
            # Check blocked paths
            for blocked in self._config.get("blocked_paths", []):
                if fnmatch.fnmatch(abs_path, blocked) or abs_path.startswith(blocked):
                    return False, f"Path is blocked: {blocked}"
            
            # Check if within workspace
            if not self.is_within_workspace(file_path):
                return False, f"Path is outside workspace: {self._workspace_path}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Path validation error: {str(e)}"
    
    def validate_file_extension(self, file_path: str) -> bool:
        """Prüfe ob die Dateierweiterung erlaubt ist"""
        ext = os.path.splitext(file_path)[1].lower()
        allowed = self._config.get("allowed_extensions", [])
        return ext in allowed
    
    def get_max_file_size(self) -> int:
        """Gib die maximale Dateigröße in Bytes zurück"""
        return self._config.get("max_file_size", 10) * 1024 * 1024
    
    def get_execution_timeout(self) -> int:
        """Gib das Timeout für Code-Ausführung in Sekunden zurück"""
        return self._config.get("execution_timeout", 30)
    
    def is_read_only(self) -> bool:
        """Prüfe ob nur-Lesen-Modus aktiviert ist"""
        return self._config.get("read_only", False)
    
    def get_config(self) -> dict:
        """Gib die vollständige Konfiguration zurück"""
        return self._config.copy()
    
    def resolve_path(self, relative_path: str) -> str:
        """
        Löse einen relativen Pfad relativ zum Workspace auf.
        Returns den absoluten Pfad innerhalb des Workspaces.
        """
        # If already absolute and within workspace, return as-is
        if os.path.isabs(relative_path):
            if self.is_within_workspace(relative_path):
                return relative_path
            else:
                # Try to find the file within workspace
                filename = os.path.basename(relative_path)
                return os.path.join(self._workspace_path, filename)
        
        # Resolve relative to workspace
        return os.path.join(self._workspace_path, relative_path)


# Globale Instanz
_workspace_manager: Optional[WorkspaceManager] = None


def get_workspace_manager(config_path: str = None) -> WorkspaceManager:
    """Gib die globale Workspace Manager Instanz zurück"""
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager(config_path)
    return _workspace_manager


def get_workspace_path() -> str:
    """Gib den aktuellen Workspace-Pfad zurück"""
    return get_workspace_manager().get_workspace_path()


def is_within_workspace(file_path: str) -> bool:
    """Prüfe ob ein Pfad innerhalb des Workspaces liegt"""
    return get_workspace_manager().is_within_workspace(file_path)


def validate_path(file_path: str) -> tuple[bool, str]:
    """Validiere einen Pfad gegen die Workspace-Regeln"""
    return get_workspace_manager().validate_path(file_path)