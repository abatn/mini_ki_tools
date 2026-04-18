# MCP Marketplace - Registry for public MCP Servers
# Registry mit öffentlichen MCP-Servern (GitHub, Slack, Database)
# Befehl: /mcp search, /mcp install <name>, /mcp update
# Konfiguration in config/mcp_marketplace.json

import json
import os
import subprocess
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class MCPServer:
    """MCP Server definition"""
    name: str
    description: str
    category: str
    provider: str
    command: str
    args: List[str] = None
    env: Dict[str, str] = None
    installed: bool = False
    version: str = "latest"
    repo_url: str = ""


class MCPMarketplace:
    """
    MCP Marketplace für öffentliche MCP-Server.
    Registry mit öffentlichen MCP-Servern (GitHub, Slack, Database).
    Befehl: /mcp search, /mcp install <name>, /mcp update.
    """
    
    DEFAULT_SERVERS = [
        MCPServer(
            name="github",
            description="GitHub integration - issues, PRs, repos",
            category="development",
            provider="microsoft",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            repo_url="https://github.com/modelcontextprotocol/servers/tree/main/github"
        ),
        MCPServer(
            name="slack",
            description="Slack integration - channels, messages",
            category="communication",
            provider="modelcontextprotocol",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-slack"],
            repo_url="https://github.com/modelcontextprotocol/servers/tree/main/slack"
        ),
        MCPServer(
            name="postgres",
            description="PostgreSQL database integration",
            category="database",
            provider="modelcontextprotocol",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres"],
            repo_url="https://github.com/modelcontextprotocol/servers/tree/main/postgres"
        ),
        MCPServer(
            name="filesystem",
            description="Local filesystem access",
            category="development",
            provider="modelcontextprotocol",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
            repo_url="https://github.com/modelcontextprotocol/servers/tree/main/filesystem"
        ),
        MCPServer(
            name="brave-search",
            description="Brave web search",
            category="search",
            provider="modelcontextprotocol",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"],
            repo_url="https://github.com/modelcontextprotocol/servers/tree/main/brave-search"
        ),
        MCPServer(
            name="puppeteer",
            description="Browser automation via Puppeteer",
            category="automation",
            provider="modelcontextprotocol",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-puppeteer"],
            repo_url="https://github.com/modelcontextprotocol/servers/tree/main/puppeteer"
        ),
        MCPServer(
            name="aws-kb-retrieval",
            description="AWS Knowledge Base retrieval",
            category="search",
            provider="modelcontextprotocol",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-aws-kb-retrieval"],
            repo_url="https://github.com/modelcontextprotocol/servers/tree/main/aws-kb-retrieval"
        ),
        MCPServer(
            name="google-maps",
            description="Google Maps integration",
            category="utilities",
            provider="modelcontextprotocol",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-google-maps"],
            repo_url="https://github.com/modelcontextprotocol/servers/tree/main/google-maps"
        ),
    ]
    
    def __init__(self, config_path: str = "config/mcp_marketplace.json"):
        self.config_path = config_path
        self.servers: Dict[str, MCPServer] = {}
        self._load_config()
    
    def _load_config(self):
        """Load marketplace configuration"""
        config_file = Path(self.config_path)
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    
                # Load servers from config
                for server_data in data.get('servers', []):
                    server = MCPServer(**server_data)
                    self.servers[server.name] = server
                    
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                self._init_default_servers()
        else:
            self._init_default_servers()
    
    def _init_default_servers(self):
        """Initialize with default servers"""
        for server in self.DEFAULT_SERVERS:
            self.servers[server.name] = server
        self._save_config()
    
    def _save_config(self):
        """Save marketplace configuration"""
        config_file = Path(self.config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "servers": [
                {
                    "name": s.name,
                    "description": s.description,
                    "category": s.category,
                    "provider": s.provider,
                    "command": s.command,
                    "args": s.args,
                    "env": s.env,
                    "installed": s.installed,
                    "version": s.version,
                    "repo_url": s.repo_url
                }
                for s in self.servers.values()
            ]
        }
        
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def search(self, query: str) -> List[MCPServer]:
        """
        Suche nach MCP-Servern.
        
        Args:
            query: Suchbegriff
            
        Returns:
            Liste von passenden Servern
        """
        query_lower = query.lower()
        results = []
        
        for server in self.servers.values():
            if (query_lower in server.name.lower() or
                query_lower in server.description.lower() or
                query_lower in server.category.lower()):
                results.append(server)
        
        return results
    
    def list_by_category(self, category: str) -> List[MCPServer]:
        """List servers by category"""
        return [s for s in self.servers.values() if s.category == category]
    
    def list_installed(self) -> List[MCPServer]:
        """List installed servers"""
        return [s for s in self.servers.values() if s.installed]
    
    def install(self, name: str) -> Dict[str, Any]:
        """
        Installiere einen MCP-Server.
        
        Args:
            name: Name des Servers
            
        Returns:
            Dict mit Ergebnis
        """
        if name not in self.servers:
            return {"success": False, "error": f"Server '{name}' not found"}
        
        server = self.servers[name]
        
        if server.installed:
            return {"success": False, "error": f"Server '{name}' already installed"}
        
        # Build install command
        cmd = [server.command] + (server.args or [])
        
        try:
            # Run installation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                server.installed = True
                self._save_config()
                return {
                    "success": True,
                    "message": f"Server '{name}' installed successfully",
                    "command": " ".join(cmd)
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "command": " ".join(cmd)
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Installation timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def uninstall(self, name: str) -> Dict[str, Any]:
        """
        Deinstalliere einen MCP-Server.
        
        Args:
            name: Name des Servers
            
        Returns:
            Dict mit Ergebnis
        """
        if name not in self.servers:
            return {"success": False, "error": f"Server '{name}' not found"}
        
        server = self.servers[name]
        
        if not server.installed:
            return {"success": False, "error": f"Server '{name}' not installed"}
        
        # For npx packages, we can't really uninstall
        # Just mark as not installed
        server.installed = False
        self._save_config()
        
        return {
            "success": True,
            "message": f"Server '{name}' marked as uninstalled (npx packages remain in cache)"
        }
    
    def update(self, name: str = None) -> Dict[str, Any]:
        """
        Update einen oder alle MCP-Server.
        
        Args:
            name: Optionaler Name, wenn None dann alle
            
        Returns:
            Dict mit Ergebnis
        """
        if name:
            servers_to_update = [self.servers[name]] if name in self.servers else []
        else:
            servers_to_update = list(self.servers.values())
        
        results = []
        
        for server in servers_to_update:
            if not server.installed:
                results.append({
                    "name": server.name,
                    "success": False,
                    "error": "Not installed"
                })
                continue
            
            # Re-run install to update
            result = self.install(server.name)
            results.append({
                "name": server.name,
                **result
            })
        
        return {
            "success": all(r.get("success", False) for r in results),
            "results": results
        }
    
    def get_config(self, name: str) -> Optional[Dict]:
        """
        Generiere Konfiguration für einen Server.
        
        Args:
            name: Name des Servers
            
        Returns:
            Dict mit Server-Konfiguration
        """
        if name not in self.servers:
            return None
        
        server = self.servers[name]
        
        return {
            "mcpServers": {
                server.name: {
                    "command": server.command,
                    "args": server.args or [],
                    "env": server.env or {}
                }
            }
        }
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories"""
        return list(set(s.category for s in self.servers.values()))
    
    def get_info(self, name: str) -> Optional[Dict]:
        """Get detailed info about a server"""
        if name not in self.servers:
            return None
        
        server = self.servers[name]
        
        return {
            "name": server.name,
            "description": server.description,
            "category": server.category,
            "provider": server.provider,
            "installed": server.installed,
            "version": server.version,
            "repo_url": server.repo_url,
            "command": server.command,
            "args": server.args
        }


# CLI interface
def main():
    """CLI interface for MCP Marketplace"""
    import sys
    
    marketplace = MCPMarketplace()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python mcp_marketplace.py search <query>")
        print("  python mcp_marketplace.py install <name>")
        print("  python mcp_marketplace.py list")
        print("  python mcp_marketplace.py list --installed")
        print("  python mcp_marketplace.py list --category <category>")
        print("  python mcp_marketplace.py update [name]")
        print("  python mcp_marketplace.py config <name>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = marketplace.search(query)
        print(f"Found {len(results)} servers:")
        for s in results:
            status = "✓ installed" if s.installed else "○ not installed"
            print(f"  - {s.name} ({s.category}) {status}")
            print(f"    {s.description}")
    
    elif command == "install" and len(sys.argv) > 2:
        name = sys.argv[2]
        result = marketplace.install(name)
        print(f"{'✓' if result['success'] else '✗'} {result.get('message', result.get('error'))}")
    
    elif command == "uninstall" and len(sys.argv) > 2:
        name = sys.argv[2]
        result = marketplace.uninstall(name)
        print(f"{'✓' if result['success'] else '✗'} {result.get('message', result.get('error'))}")
    
    elif command == "list":
        if len(sys.argv) > 2 and sys.argv[2] == "--installed":
            servers = marketplace.list_installed()
            print(f"Installed servers ({len(servers)}):")
        elif len(sys.argv) > 2 and sys.argv[2] == "--category":
            category = sys.argv[3] if len(sys.argv) > 3 else ""
            servers = marketplace.list_by_category(category)
            print(f"Servers in category '{category}' ({len(servers)}):")
        else:
            servers = list(marketplace.servers.values())
            print(f"All available servers ({len(servers)}):")
        
        for s in servers:
            status = "✓" if s.installed else "○"
            print(f"  {status} {s.name} - {s.description}")
    
    elif command == "update":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        result = marketplace.update(name)
        print(f"Update {'successful' if result['success'] else 'partial'}")
        for r in result.get('results', []):
            print(f"  {r['name']}: {'✓' if r.get('success') else '✗'}")
    
    elif command == "config" and len(sys.argv) > 2:
        name = sys.argv[2]
        config = marketplace.get_config(name)
        if config:
            print(json.dumps(config, indent=2))
        else:
            print(f"Server '{name}' not found")
    
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()