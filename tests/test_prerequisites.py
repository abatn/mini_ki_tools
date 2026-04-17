# tests/test_prerequisites.py

import sys
import os
import subprocess

def test_python_version():
    assert sys.version_info >= (3, 12), "Python version is not 3.12 or higher"

def test_create_virtual_environment():
    project_dir = os.path.join(os.getcwd(), "..")
    venv_path = os.path.join(project_dir, "venv")

    # Check if the virtual environment already exists
    assert not os.path.exists(venv_path), "Virtual environment already exists"

    # Create the virtual environment
    subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)

    # Verify that the virtual environment was created successfully
    assert os.path.exists(os.path.join(venv_path, "bin", "python")), "Virtual environment not created correctly"