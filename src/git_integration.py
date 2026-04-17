import subprocess
import os
from typing import List, Dict, Optional

class GitIntegration:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        
    def commit(self, message: str, files: List[str] = None) -> Dict[str, str]:
        """Commit changes to the repository"""
        try:
            if files:
                cmd = ["git", "add"] + files
                subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True)
            
            cmd = ["git", "commit", "-m", message]
            result = subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True, text=True)
            
            return {
                "success": True,
                "message": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": None,
                "error": str(e.stderr)
            }
    
    def branch(self, branch_name: str, create: bool = True) -> Dict[str, str]:
        """Create or switch to a branch"""
        try:
            if create:
                cmd = ["git", "checkout", "-b", branch_name]
            else:
                cmd = ["git", "checkout", branch_name]
            
            result = subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True, text=True)
            
            return {
                "success": True,
                "message": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": None,
                "error": str(e.stderr)
            }
    
    def merge(self, branch_name: str, commit: bool = False) -> Dict[str, str]:
        """Merge a branch into current branch"""
        try:
            if commit:
                cmd = ["git", "merge", "--no-ff", branch_name]
            else:
                cmd = ["git", "merge", branch_name]
            
            result = subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True, text=True)
            
            return {
                "success": True,
                "message": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": None,
                "error": str(e.stderr)
            }
    
    def diff(self, file_path: str = None) -> Dict[str, str]:
        """Show changes in working directory or specific file"""
        try:
            if file_path:
                cmd = ["git", "diff", file_path]
            else:
                cmd = ["git", "diff"]
            
            result = subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True, text=True)
            
            return {
                "success": True,
                "message": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": None,
                "error": str(e.stderr)
            }
    
    def blame(self, file_path: str) -> Dict[str, str]:
        """Show who modified each line of a file"""
        try:
            cmd = ["git", "blame", file_path]
            result = subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True, text=True)
            
            return {
                "success": True,
                "message": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": None,
                "error": str(e.stderr)
            }
    
    def revert(self, commit_hash: str) -> Dict[str, str]:
        """Revert a specific commit"""
        try:
            cmd = ["git", "revert", commit_hash]
            result = subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True, text=True)
            
            return {
                "success": True,
                "message": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": None,
                "error": str(e.stderr)
            }
    
    def cherry_pick(self, commit_hash: str) -> Dict[str, str]:
        """Apply changes from a commit to current branch"""
        try:
            cmd = ["git", "cherry-pick", commit_hash]
            result = subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True, text=True)
            
            return {
                "success": True,
                "message": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": None,
                "error": str(e.stderr)
            }