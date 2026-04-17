import json
import os
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class UndoManager:
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self.current_index = -1
        
    def add_action(self, action_type: str, files: List[str], old_content: str = None, 
                  new_content: str = None, command: str = None, result: str = None):
        """Add an action to history"""
        try:
            # Remove future actions if we're not at the end
            if self.current_index < len(self.history) - 1:
                self.history = self.history[:self.current_index + 1]
            
            action = {
                'type': action_type,
                'files': files,
                'old_content': old_content,
                'new_content': new_content,
                'command': command,
                'result': result,
                'timestamp': time.time()
            }
            
            self.history.append(action)
            self.current_index = len(self.history) - 1
            
            # Limit history size
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
                self.current_index = len(self.history) - 1
                
        except Exception as e:
            logger.error(f"Error adding action to history: {str(e)}")
    
    def undo(self) -> Optional[Dict[str, Any]]:
        """Undo last action"""
        try:
            if self.current_index < 0:
                return None
                
            action = self.history[self.current_index]
            self.current_index -= 1
            return action
        except Exception as e:
            logger.error(f"Error undoing action: {str(e)}")
            return None
    
    def redo(self) -> Optional[Dict[str, Any]]:
        """Redo last undone action"""
        try:
            if self.current_index >= len(self.history) - 1:
                return None
                
            self.current_index += 1
            return self.history[self.current_index]
        except Exception as e:
            logger.error(f"Error redoing action: {str(e)}")
            return None
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get full history"""
        return self.history[:self.current_index + 1]
    
    def clear_history(self):
        """Clear all history"""
        self.history = []
        self.current_index = -1
    
    def get_action_summary(self) -> str:
        """Get human-readable summary of history"""
        if not self.history:
            return "No actions in history"
        
        actions = []
        for i, action in enumerate(self.history[-5:]):  # Last 5 actions
            actions.append(f"{i+1}. {action['type']} on {len(action['files'])} files")
        
        return "\n".join(actions)