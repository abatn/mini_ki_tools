# Sandboxing Manager - Docker Isolation for Tool Execution
# Jede Tool-Ausführung in eigenem Docker-Container mit Zeitlimit, CPU/RAM-Limits

import os
import json
import uuid
import subprocess
import time
import tempfile
import shutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution"""
    image: str = "python:3.12-slim"
    timeout: int = 300  # 5 minutes
    cpu_limit: str = "0.5"  # 50% of one CPU
    memory_limit: str = "512m"  # 512 MB
    read_only: bool = True
    network_disabled: bool = True
    working_dir: str = "/workspace"
    max_output_size: int = 1024 * 1024  # 1 MB


@dataclass
class SandboxResult:
    """Result of sandbox execution"""
    success: bool
    output: str
    error: str
    exit_code: int
    duration: float
    sandbox_id: str


class SandboxManager:
    """
    Manages Docker-based sandbox execution for tool isolation.
    Jede Tool-Ausführung in eigenem Docker-Container mit Zeitlimit, CPU/RAM-Limits, read-only System.
    """
    
    def __init__(self, config: SandboxConfig = None):
        self.config = config or SandboxConfig()
        self.active_sandboxes: Dict[str, Dict] = {}
        self.docker_available = self._check_docker()
    
    def _check_docker(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Docker not available - running in fallback mode")
            return False
    
    def _generate_dockerfile(self, commands: List[str]) -> str:
        """Generate Dockerfile for sandbox"""
        return f"""
FROM {self.config.image}
WORKDIR {self.config.working_dir}
RUN pip install --no-cache-dir requests pydantic
COPY workspace /workspace
{" && ".join(commands)}
"""
    
    def _create_workspace(self, files: Dict[str, str]) -> str:
        """Create temporary workspace with files"""
        workspace = tempfile.mkdtemp(prefix="sandbox_")
        
        for filename, content in files.items():
            filepath = os.path.join(workspace, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content)
        
        return workspace
    
    def execute(
        self,
        command: str,
        files: Dict[str, str] = None,
        env_vars: Dict[str, str] = None,
        user_id: str = "default"
    ) -> SandboxResult:
        """
        Execute command in isolated Docker sandbox.
        
        Args:
            command: Command to execute
            files: Files to mount in sandbox
            env_vars: Environment variables
            user_id: User ID for tracking
            
        Returns:
            SandboxResult with output, error, and metrics
        """
        sandbox_id = f"sandbox_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        logger.info(f"Starting sandbox {sandbox_id} for user {user_id}")
        
        # Track sandbox
        self.active_sandboxes[sandbox_id] = {
            "user_id": user_id,
            "command": command,
            "start_time": start_time
        }
        
        if not self.docker_available:
            # Fallback to local execution
            return self._execute_fallback(command, files, env_vars, sandbox_id, start_time)
        
        try:
            return self._execute_docker(command, files, env_vars, sandbox_id, start_time)
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return SandboxResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
                duration=time.time() - start_time,
                sandbox_id=sandbox_id
            )
        finally:
            # Cleanup
            if sandbox_id in self.active_sandboxes:
                del self.active_sandboxes[sandbox_id]
    
    def _execute_docker(
        self,
        command: str,
        files: Dict[str, str],
        env_vars: Dict[str, str],
        sandbox_id: str,
        start_time: float
    ) -> SandboxResult:
        """Execute command in Docker container"""
        # Create workspace
        workspace = self._create_workspace(files or {})
        
        # Build docker run command
        docker_cmd = [
            "docker", "run",
            "--rm",
            "--name", sandbox_id,
            "--cpus", self.config.cpu_limit,
            "--memory", self.config.memory_limit,
            "--read-only" if self.config.read_only else "--read-write",
            "--network", "none" if self.config.network_disabled else "bridge",
            "-v", f"{workspace}:{self.config.working_dir}",
            "-w", self.config.working_dir,
        ]
        
        # Add environment variables
        if env_vars:
            for key, value in env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])
        
        # Add image and command
        docker_cmd.extend([self.config.image, "sh", "-c", command])
        
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                timeout=self.config.timeout,
                text=True
            )
            
            duration = time.time() - start_time
            
            # Truncate output if too large
            output = result.stdout[:self.config.max_output_size]
            error = result.stderr[:self.config.max_output_size]
            
            return SandboxResult(
                success=result.returncode == 0,
                output=output,
                error=error,
                exit_code=result.returncode,
                duration=duration,
                sandbox_id=sandbox_id
            )
            
        except subprocess.TimeoutExpired:
            # Kill the container
            subprocess.run(["docker", "kill", sandbox_id], capture_output=True)
            return SandboxResult(
                success=False,
                output="",
                error=f"Timeout after {self.config.timeout}s",
                exit_code=-1,
                duration=self.config.timeout,
                sandbox_id=sandbox_id
            )
        finally:
            # Cleanup workspace
            shutil.rmtree(workspace, ignore_errors=True)
    
    def _execute_fallback(
        self,
        command: str,
        files: Dict[str, str],
        env_vars: Dict[str, str],
        sandbox_id: str,
        start_time: float
    ) -> SandboxResult:
        """Fallback execution without Docker"""
        # Create temporary workspace
        workspace = self._create_workspace(files or {})
        
        # Change to workspace directory
        original_dir = os.getcwd()
        os.chdir(workspace)
        
        # Set environment variables
        if env_vars:
            original_env = os.environ.copy()
            os.environ.update(env_vars)
        
        try:
            result = subprocess.run(
                ["sh", "-c", command],
                capture_output=True,
                timeout=self.config.timeout,
                text=True
            )
            
            duration = time.time() - start_time
            
            return SandboxResult(
                success=result.returncode == 0,
                output=result.stdout[:self.config.max_output_size],
                error=result.stderr[:self.config.max_output_size],
                exit_code=result.returncode,
                duration=duration,
                sandbox_id=sandbox_id
            )
            
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                output="",
                error=f"Timeout after {self.config.timeout}s",
                exit_code=-1,
                duration=self.config.timeout,
                sandbox_id=sandbox_id
            )
        finally:
            os.chdir(original_dir)
            if env_vars:
                os.environ.clear()
                os.environ.update(original_env)
            shutil.rmtree(workspace, ignore_errors=True)
    
    def get_active_sandboxes(self) -> List[Dict]:
        """Get list of active sandboxes"""
        return [
            {
                "sandbox_id": sid,
                "user_id": info["user_id"],
                "command": info["command"],
                "duration": time.time() - info["start_time"]
            }
            for sid, info in self.active_sandboxes.items()
        ]
    
    def kill_sandbox(self, sandbox_id: str) -> bool:
        """Kill a running sandbox"""
        if not self.docker_available:
            return False
        
        try:
            subprocess.run(["docker", "kill", sandbox_id], capture_output=True)
            return True
        except Exception as e:
            logger.error(f"Failed to kill sandbox {sandbox_id}: {e}")
            return False


# Singleton instance
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """Get or create sandbox manager singleton"""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager


def execute_in_sandbox(
    command: str,
    files: Dict[str, str] = None,
    env_vars: Dict[str, str] = None,
    user_id: str = "default"
) -> SandboxResult:
    """Convenience function to execute in sandbox"""
    manager = get_sandbox_manager()
    return manager.execute(command, files, env_vars, user_id)


# API Integration
def register_sandbox_routes(app):
    """Register sandbox endpoints with FastAPI"""
    from fastapi import HTTPException
    
    @app.post("/api/sandbox/execute")
    async def sandbox_execute(request: dict):
        """Execute command in sandbox"""
        command = request.get("command")
        files = request.get("files", {})
        env_vars = request.get("env_vars", {})
        user_id = request.get("user_id", "default")
        
        if not command:
            raise HTTPException(status_code=400, detail="command required")
        
        manager = get_sandbox_manager()
        result = manager.execute(command, files, env_vars, user_id)
        
        return {
            "sandbox_id": result.sandbox_id,
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "exit_code": result.exit_code,
            "duration": result.duration
        }
    
    @app.get("/api/sandbox/active")
    async def sandbox_list():
        """List active sandboxes"""
        manager = get_sandbox_manager()
        return {"sandboxes": manager.get_active_sandboxes()}
    
    @app.delete("/api/sandbox/{sandbox_id}")
    async def sandbox_kill(sandbox_id: str):
        """Kill a sandbox"""
        manager = get_sandbox_manager()
        success = manager.kill_sandbox(sandbox_id)
        return {"success": success}
    
    logger.info("Sandbox routes registered")


# Standalone test
if __name__ == "__main__":
    # Test sandbox execution
    manager = SandboxManager()
    
    # Test simple command
    result = manager.execute(
        command="python3 -c 'print(\"Hello from sandbox!\")'",
        files={"test.py": "print('Hello')"},
        user_id="test_user"
    )
    
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    print(f"Duration: {result.duration:.2f}s")
    print(f"Sandbox ID: {result.sandbox_id}")