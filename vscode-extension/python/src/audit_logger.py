# Audit Logger - Compliance and Security Logging
# Jede Aktion protokollieren mit Verschlüsselung

import os
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Try to import cryptography for Fernet encryption
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography not available - audit logs will not be encrypted")


@dataclass
class AuditEntry:
    """Single audit log entry"""
    id: str
    user_id: str
    timestamp: str
    action_type: str
    file_path: Optional[str]
    prompt: Optional[str]
    result: Optional[str]
    success: bool
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)


class AuditLogger:
    """
    Audit Logger for compliance and security.
    Jede Aktion protokollieren (user_id, timestamp, action_type, file, prompt, result).
    Verschlüsselung mit Fernet.
    """
    
    def __init__(self, log_dir: str = "logs/audit", encryption_key: str = None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption
        self.cipher = None
        if CRYPTO_AVAILABLE:
            if encryption_key:
                self.cipher = Fernet(encryption_key.encode())
            else:
                # Try to load or generate key
                key_file = self.log_dir / ".key"
                if key_file.exists():
                    with open(key_file, 'rb') as f:
                        key = f.read()
                        self.cipher = Fernet(key)
                else:
                    # Generate new key
                    key = Fernet.generate_key()
                    key_file.write_bytes(key)
                    self.cipher = Fernet(key)
                    logger.info(f"Generated new encryption key: {key_file}")
        
        self.current_log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m')}.jsonl"
    
    def _encrypt(self, data: str) -> str:
        """Encrypt data using Fernet"""
        if self.cipher:
            return self.cipher.encrypt(data.encode()).decode()
        return data
    
    def _decrypt(self, data: str) -> str:
        """Decrypt data using Fernet"""
        if self.cipher:
            try:
                return self.cipher.decrypt(data.encode()).decode()
            except Exception:
                return data
        return data
    
    def log(
        self,
        user_id: str,
        action_type: str,
        file_path: str = None,
        prompt: str = None,
        result: str = None,
        success: bool = True,
        metadata: Dict = None
    ) -> str:
        """
        Log an action to the audit log.
        
        Args:
            user_id: User identifier
            action_type: Type of action (read, write, execute, etc.)
            file_path: File involved in the action
            prompt: Prompt or command executed
            result: Result of the action
            success: Whether action was successful
            metadata: Additional metadata
            
        Returns:
            Audit entry ID
        """
        entry_id = str(uuid.uuid4())
        
        entry = AuditEntry(
            id=entry_id,
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            file_path=file_path,
            prompt=prompt,
            result=result,
            success=success,
            metadata=metadata or {}
        )
        
        # Convert to JSON
        entry_json = json.dumps(entry.to_dict())
        
        # Encrypt if enabled
        if self.cipher:
            entry_json = self._encrypt(entry_json)
        
        # Write to log file
        with open(self.current_log_file, 'a') as f:
            f.write(entry_json + '\n')
        
        logger.info(f"Audit log: {user_id} - {action_type} - {entry_id}")
        return entry_id
    
    def search(
        self,
        user_id: str = None,
        action_type: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """
        Search audit logs with filters.
        
        Args:
            user_id: Filter by user ID
            action_type: Filter by action type
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            limit: Maximum number of results
            
        Returns:
            List of matching audit entries
        """
        results = []
        
        # Read all log files
        log_files = sorted(self.log_dir.glob("audit_*.jsonl"), reverse=True)
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry_json = line.strip()
                            
                            # Decrypt if needed
                            if self.cipher:
                                try:
                                    entry_json = self._decrypt(entry_json)
                                except Exception:
                                    continue
                            
                            entry_dict = json.loads(entry_json)
                            entry = AuditEntry(**entry_dict)
                            
                            # Apply filters
                            if user_id and entry.user_id != user_id:
                                continue
                            if action_type and entry.action_type != action_type:
                                continue
                            if start_date and entry.timestamp < start_date:
                                continue
                            if end_date and entry.timestamp > end_date:
                                continue
                            
                            results.append(entry)
                            
                            if len(results) >= limit:
                                return results
                                
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
        
        return results
    
    def export(
        self,
        output_path: str = None,
        format: str = "json",
        start_date: str = None,
        end_date: str = None
    ) -> Dict:
        """
        Export audit logs to file.
        
        Args:
            output_path: Output file path
            format: Export format (json, csv)
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Export result with path and count
        """
        if output_path is None:
            output_path = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        entries = self.search(start_date=start_date, end_date=end_date, limit=10000)
        
        if format == "json":
            with open(output_path, 'w') as f:
                json.dump([e.to_dict() for e in entries], f, indent=2)
        elif format == "csv":
            import csv
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'user_id', 'timestamp', 'action_type', 'file_path', 'prompt', 'result', 'success'])
                for e in entries:
                    writer.writerow([e.id, e.user_id, e.timestamp, e.action_type, e.file_path, e.prompt, e.result, e.success])
        
        logger.info(f"Exported {len(entries)} audit entries to {output_path}")
        return {
            "status": "success",
            "path": output_path,
            "count": len(entries)
        }
    
    def get_stats(self, days: int = 7) -> Dict:
        """Get audit statistics for the last N days"""
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        entries = self.search(start_date=start_date, limit=10000)
        
        # Calculate statistics
        total = len(entries)
        successful = sum(1 for e in entries if e.success)
        failed = total - successful
        
        # Group by action type
        action_counts = {}
        for e in entries:
            action_counts[e.action_type] = action_counts.get(e.action_type, 0) + 1
        
        # Group by user
        user_counts = {}
        for e in entries:
            user_counts[e.user_id] = user_counts.get(e.user_id, 0) + 1
        
        return {
            "period_days": days,
            "total_actions": total,
            "successful": successful,
            "failed": failed,
            "action_types": action_counts,
            "top_users": sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create audit logger singleton"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def log_action(
    user_id: str,
    action_type: str,
    file_path: str = None,
    prompt: str = None,
    result: str = None,
    success: bool = True,
    metadata: Dict = None
) -> str:
    """Convenience function to log an action"""
    logger = get_audit_logger()
    return logger.log(user_id, action_type, file_path, prompt, result, success, metadata)


# API Integration
def register_audit_routes(app):
    """Register audit endpoints with FastAPI"""
    from fastapi import HTTPException
    
    @app.post("/api/audit/log")
    async def audit_log(request: dict):
        """Log an action to audit"""
        user_id = request.get("user_id", "anonymous")
        action_type = request.get("action_type", "unknown")
        
        entry_id = log_action(
            user_id=user_id,
            action_type=action_type,
            file_path=request.get("file_path"),
            prompt=request.get("prompt"),
            result=request.get("result"),
            success=request.get("success", True),
            metadata=request.get("metadata", {})
        )
        
        return {"status": "success", "entry_id": entry_id}
    
    @app.get("/api/audit/search")
    async def audit_search(
        user_id: str = None,
        action_type: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100
    ):
        """Search audit logs"""
        logger = get_audit_logger()
        entries = logger.search(user_id, action_type, start_date, end_date, limit)
        return {
            "count": len(entries),
            "entries": [e.to_dict() for e in entries]
        }
    
    @app.get("/api/audit/export")
    async def audit_export(
        path: str = None,
        format: str = "json",
        start_date: str = None,
        end_date: str = None
    ):
        """Export audit logs"""
        logger = get_audit_logger()
        return logger.export(path, format, start_date, end_date)
    
    @app.get("/api/audit/stats")
    async def audit_stats(days: int = 7):
        """Get audit statistics"""
        logger = get_audit_logger()
        return logger.get_stats(days)
    
    logger.info("Audit routes registered")


# Standalone test
if __name__ == "__main__":
    # Test audit logging
    logger = AuditLogger()
    
    # Log some actions
    log_action(
        user_id="user1",
        action_type="read",
        file_path="/home/user/file.py",
        prompt="Read file",
        result="Success",
        success=True
    )
    
    log_action(
        user_id="user1",
        action_type="write",
        file_path="/home/user/output.txt",
        prompt="Write content",
        result="Success",
        success=True
    )
    
    log_action(
        user_id="user2",
        action_type="execute",
        prompt="python script.py",
        result="Error: timeout",
        success=False
    )
    
    # Search logs
    results = logger.search(user_id="user1")
    print(f"Found {len(results)} entries for user1")
    
    # Get stats
    stats = logger.get_stats()
    print(f"Stats: {stats}")
    
    # Export
    export_result = logger.export("audit_test.json")
    print(f"Export: {export_result}")