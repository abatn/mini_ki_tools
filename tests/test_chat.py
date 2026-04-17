# tests/test_chat.py

import pytest
from src.thought_action_observation import ThoughtActionObservation

def test_chat():
    chat = ThoughtActionObservation()
    result = chat.process(">> hilf mir, CSV zu laden")
    assert "Thought" in result and "Action" in result and "Observation" in result