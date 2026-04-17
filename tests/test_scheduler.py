# tests/test_scheduler.py

import pytest
from src.scheduler import Scheduler

def test_scheduler():
    scheduler = Scheduler()
    result = scheduler.schedule_job("print('Hallo')", 1)
    assert result is not None