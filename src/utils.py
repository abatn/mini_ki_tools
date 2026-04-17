import os
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create necessary directories"""
    directories = ['logs', 'data', 'src', 'temp']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    logger.info("Created necessary directories")

def load_config(config_file: str = "config.json") -> Dict[str, Any]:
    """Load configuration from file"""
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            # Return default config
            return {
                "model": "llama3.2",
                "ollama_url": "http://localhost:11434",
                "max_tokens": 2048,
                "temperature": 0.7
            }
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}

def save_config(config: Dict[str, Any], config_file: str = "config.json"):
    """Save configuration to file"""
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved successfully")
    except Exception as e:
        logger.error(f"Error saving config: {str(e)}")

def validate_file_path(filepath: str) -> bool:
    """Validate if file path is safe"""
    try:
        # Check if path is within allowed directories
        abs_path = os.path.abspath(filepath)
        allowed_paths = [os.path.abspath(p) for p in ['data', 'src', 'temp']]
        
        for allowed_path in allowed_paths:
            if abs_path.startswith(allowed_path):
                return True
        return False
    except Exception as e:
        logger.error(f"Error validating file path: {str(e)}")
        return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal"""
    # Remove directory traversal sequences
    filename = filename.replace('../', '').replace('..\\', '')
    # Remove leading and trailing whitespace
    filename = filename.strip()
    return filename

def get_file_extension(filepath: str) -> str:
    """Get file extension"""
    return os.path.splitext(filepath)[1]

def is_text_file(filepath: str) -> bool:
    """Check if file is a text file"""
    try:
        with open(filepath, 'r') as f:
            f.read(1024)  # Try to read first 1KB
        return True
    except:
        return False

def format_response(response: str, max_length: int = 1000) -> str:
    """Format response to avoid overly long outputs"""
    if len(response) > max_length:
        return response[:max_length] + "... (truncated)"
    return response