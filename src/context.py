import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class ProjectContext:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.context_data = {}
        self.last_edited_files = []
        self.backup_dir = Path(".agent_backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    def scan_project(self) -> Dict[str, Any]:
        """Scan project for context information"""
        try:
            # Scan all files in project (excluding common ignored directories)
            ignored_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.env'}
            files = []
            
            for root, dirs, filenames in os.walk(self.project_root):
                # Filter out ignored directories
                dirs[:] = [d for d in dirs if d not in ignored_dirs]
                
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, self.project_root)
                    files.append({
                        'path': rel_path,
                        'size': os.path.getsize(file_path),
                        'modified': time.ctime(os.path.getmtime(file_path))
                    })
            
            # Get last edited files from log
            last_edited = self._get_last_edited_files()
            
            # Get environment info
            env_info = self._get_environment_info()
            
            self.context_data = {
                'project_root': str(self.project_root),
                'total_files': len(files),
                'files': files[:100],  # Limit to first 100 files
                'last_edited_files': last_edited,
                'environment': env_info,
                'scan_timestamp': time.time()
            }
            
            return self.context_data
            
        except Exception as e:
            logger.error(f"Error scanning project: {str(e)}")
            return {}
    
    def _get_last_edited_files(self) -> List[Dict[str, Any]]:
        """Get last edited files from log"""
        try:
            # Simple implementation - in real app would read from log file
            return [
                {'path': 'src/agent.py', 'timestamp': time.time() - 3600},
                {'path': 'src/tools.py', 'timestamp': time.time() - 7200},
                {'path': 'agent_server.py', 'timestamp': time.time() - 10800},
            ][:5]  # Last 5 files
        except Exception as e:
            logger.error(f"Error getting last edited files: {str(e)}")
            return []
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """Get environment information"""
        try:
            import sys
            import subprocess
            
            env_info = {
                'python_version': sys.version,
                'python_path': sys.executable,
                'current_working_dir': os.getcwd(),
                'path': os.environ.get('PATH', ''),
                'git_branch': self._get_git_branch(),
                'system': os.name
            }
            
            return env_info
        except Exception as e:
            logger.error(f"Error getting environment info: {str(e)}")
            return {}
    
    def _get_git_branch(self) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "not_a_git_repo"
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context"""
        if not self.context_data:
            self.scan_project()
        return self.context_data
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        context = self.get_context()
        if not context:
            return "No context available"
        
        files = context.get('total_files', 0)
        last_edited = len(context.get('last_edited_files', []))
        
        return f"Project context: {files} files, last edited {last_edited} files"