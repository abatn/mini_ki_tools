# tests/test_git_integration.py

import pytest
from src.git_integration import GitIntegration

def test_git_integration():
    git = GitIntegration()
    result = git.status()
    assert "On branch" in result and "nothing to commit" in result or "Changes not staged for commit"