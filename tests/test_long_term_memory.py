# tests/test_long_term_memory.py

import pytest
from src.long_term_memory import LongTermMemory

def test_long_term_memory():
    memory = LongTermMemory()
    result = memory.store("Ein Testeintrag")
    assert "Ein Testeintrag" in memory.retrieve_all()