# tests/test_python_version.py

import sys

def test_python_version():
    assert sys.version_info >= (3, 12), "Python version is not 3.12 or higher"