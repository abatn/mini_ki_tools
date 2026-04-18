# Config Exporter/Importer for Mini KI Tools
# Export and import complete agent configuration as .agentconfig (YAML)

import os
import json
import yaml
import shutil
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = "config"
DEFAULT_PLUGINS_DIR = "plugins"
DEFAULT_OUTPUT_FILE = "config.agentconfig"


class ConfigExporter:
    """Export complete agent configuration to .agentconfig file"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.config_dir = self.base_path / DEFAULT_CONFIG_DIR
        self.plugins_dir = self.base_path / DEFAULT_PLUGINS_DIR
    
    def export(self, output_path: str = None) -> Dict[str, Any]:
        """Export all configuration to YAML file"""
        if output_path is None:
            output_path = self.base_path / DEFAULT_OUTPUT_FILE
        else:
            output_path = Path(output_path)
        
        config = {
            "version": "1.0.0",
            "exported_at": datetime.now().isoformat(),
            "models": self._export_models(),
            "tools": self._export_tools(),
            "mcp_servers": self._export_mcp_servers(),
            "plugins": self._export_plugins(),
            "context_providers": self._export_context(),
            "scheduler_jobs": self._export_scheduler(),
            "git_config": self._export_git_config()
        }
        
        # Write to YAML file
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration exported to {output_path}")
        return {"status": "success", "path": str(output_path), "config": config}
    
    def _export_models(self) -> List[Dict]:
        """Export model configurations"""
        models = []
        # Check for .continue config
        continue_config = self.base_path / ".continue" / "config.yaml"
        if continue_config.exists():
            try:
                with open(continue_config, 'r') as f:
                    data = yaml.safe_load(f)
                    models = data.get('models', [])
            except Exception as e:
                logger.warning(f"Could not read .continue config: {e}")
        return models
    
    def _export_tools(self) -> List[Dict]:
        """Export tool configurations"""
        tools = []
        continue_config = self.base_path / ".continue" / "config.yaml"
        if continue_config.exists():
            try:
                with open(continue_config, 'r') as f:
                    data = yaml.safe_load(f)
                    tools = data.get('tools', [])
            except Exception as e:
                logger.warning(f"Could not read .continue config: {e}")
        return tools
    
    def _export_mcp_servers(self) -> List[Dict]:
        """Export MCP server configurations"""
        mcp_config = self.config_dir / "mcp_servers.json"
        if mcp_config.exists():
            try:
                with open(mcp_config, 'r') as f:
                    data = json.load(f)
                    return data.get('servers', [])
            except Exception as e:
                logger.warning(f"Could not read MCP config: {e}")
        return []
    
    def _export_plugins(self) -> List[Dict]:
        """Export plugin configurations"""
        plugins = []
        if self.plugins_dir.exists():
            for plugin_file in self.plugins_dir.glob("*.py"):
                if plugin_file.name.startswith("__"):
                    continue
                plugins.append({
                    "name": plugin_file.stem,
                    "path": str(plugin_file.relative_to(self.base_path)),
                    "enabled": True
                })
        return plugins
    
    def _export_context(self) -> List[str]:
        """Export context providers"""
        continue_config = self.base_path / ".continue" / "config.yaml"
        if continue_config.exists():
            try:
                with open(continue_config, 'r') as f:
                    data = yaml.safe_load(f)
                    return data.get('context', [])
            except Exception as e:
                logger.warning(f"Could not read .continue config: {e}")
        return []
    
    def _export_scheduler(self) -> List[Dict]:
        """Export scheduler jobs (placeholder - would need runtime state)"""
        return []
    
    def _export_git_config(self) -> Dict:
        """Export git configuration"""
        git_config = {}
        git_dir = self.base_path / ".git"
        if git_dir.exists():
            git_config["initialized"] = True
            try:
                config_file = self.base_path / ".git" / "config"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        git_config["config_content"] = f.read()
            except Exception as e:
                logger.warning(f"Could not read git config: {e}")
        return git_config


class ConfigImporter:
    """Import configuration from .agentconfig file"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.config_dir = self.base_path / DEFAULT_CONFIG_DIR
        self.plugins_dir = self.base_path / DEFAULT_PLUGINS_DIR
    
    def import_config(self, input_path: str, merge: bool = True) -> Dict[str, Any]:
        """Import configuration from YAML file"""
        input_path = Path(input_path)
        
        if not input_path.exists():
            return {"status": "error", "message": f"File not found: {input_path}"}
        
        try:
            with open(input_path, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            return {"status": "error", "message": f"Invalid YAML: {e}"}
        
        results = {
            "status": "success",
            "imported": {}
        }
        
        # Import MCP servers
        if 'mcp_servers' in config:
            mcp_result = self._import_mcp_servers(config['mcp_servers'], merge)
            results["imported"]["mcp_servers"] = mcp_result
        
        # Import plugins
        if 'plugins' in config:
            plugin_result = self._import_plugins(config['plugins'])
            results["imported"]["plugins"] = plugin_result
        
        # Import .continue config
        if 'models' in config or 'tools' in config or 'context' in config:
            continue_result = self._import_continue_config(config, merge)
            results["imported"]["continue_config"] = continue_result
        
        logger.info(f"Configuration imported from {input_path}")
        return results
    
    def _import_mcp_servers(self, servers: List[Dict], merge: bool) -> Dict:
        """Import MCP server configurations"""
        self.config_dir.mkdir(exist_ok=True)
        mcp_file = self.config_dir / "mcp_servers.json"
        
        existing = []
        if merge and mcp_file.exists():
            try:
                with open(mcp_file, 'r') as f:
                    existing = json.load(f).get('servers', [])
            except:
                pass
        
        # Merge servers (avoid duplicates by name)
        existing_names = {s['name'] for s in existing}
        for server in servers:
            if server.get('name') not in existing_names:
                existing.append(server)
        
        with open(mcp_file, 'w') as f:
            json.dump({"servers": existing}, f, indent=2)
        
        return {"count": len(existing), "file": str(mcp_file)}
    
    def _import_plugins(self, plugins: List[Dict]) -> Dict:
        """Import plugin configurations"""
        self.plugins_dir.mkdir(exist_ok=True)
        
        imported = []
        for plugin in plugins:
            plugin_path = plugin.get('path')
            if plugin_path:
                src = self.base_path / plugin_path
                if src.exists():
                    imported.append(plugin.get('name'))
        
        return {"count": len(imported), "plugins": imported}
    
    def _import_continue_config(self, config: Dict, merge: bool) -> Dict:
        """Import .continue config"""
        continue_dir = self.base_path / ".continue"
        continue_dir.mkdir(exist_ok=True)
        continue_file = continue_dir / "config.yaml"
        
        existing = {}
        if merge and continue_file.exists():
            try:
                with open(continue_file, 'r') as f:
                    existing = yaml.safe_load(f) or {}
            except:
                pass
        
        # Merge models
        if 'models' in config:
            existing['models'] = config['models']
        
        # Merge tools
        if 'tools' in config:
            existing['tools'] = config['tools']
        
        # Merge context
        if 'context_providers' in config:
            existing['context'] = config['context_providers']
        
        with open(continue_file, 'w') as f:
            yaml.dump(existing, f, default_flow_style=False)
        
        return {"file": str(continue_file)}


# CLI Commands
def handle_export_command(args: List[str] = None) -> Dict:
    """Handle /export command"""
    output_path = args[0] if args else None
    exporter = ConfigExporter()
    return exporter.export(output_path)


def handle_import_command(args: List[str] = None) -> Dict:
    """Handle /import command"""
    if not args:
        return {"status": "error", "message": "Usage: /import <file_path>"}
    
    input_path = args[0]
    importer = ConfigImporter()
    return importer.import_config(input_path)


def register_config_exporter_routes(app):
    """Register export/import routes with FastAPI app"""
    from fastapi import HTTPException
    
    @app.get("/api/config/export")
    async def export_config():
        """Export current configuration"""
        exporter = ConfigExporter()
        return exporter.export()
    
    @app.post("/api/config/import")
    async def import_config(request: dict):
        """Import configuration from file"""
        input_path = request.get("path")
        merge = request.get("merge", True)
        
        if not input_path:
            raise HTTPException(status_code=400, detail="path required")
        
        importer = ConfigImporter()
        return importer.import_config(input_path, merge)
    
    @app.get("/api/config/export/download")
    async def download_config():
        """Download configuration file"""
        exporter = ConfigExporter()
        result = exporter.export()
        return result
    
    logger.info("Config exporter routes registered")


# Standalone test
if __name__ == "__main__":
    # Test export
    exporter = ConfigExporter()
    result = exporter.export("test_config.agentconfig")
    print("Export:", result)
    
    # Test import
    importer = ConfigImporter()
    result = importer.import_config("test_config.agentconfig")
    print("Import:", result)