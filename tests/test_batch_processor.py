# tests/test_batch_processor.py

import pytest
from src.batch_processor import BatchProcessor

def test_batch_processor():
    processor = BatchProcessor()
    result = processor.process_batch(["Eintrag1", "Eintrag2"])
    assert "Eintrag1" in result and "Eintrag2" in result