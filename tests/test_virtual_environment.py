# tests/test_virtual_environment.py

import os
import subprocess

def test_create_virtual_environment():
    # Navigate to the project directory
    project_dir = os.path.join(os.getcwd(), "..")
    venv_path = os.path.join(project_dir, "venv")

    # Check if the virtual environment already exists
    assert not os.path.exists(venv_path), "Virtual environment already exists"

    # Create the virtual environment
    subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)

    # Verify that the virtual environment was created successfully
    assert os.path.exists(os.path.join(venv_path, "bin", "python")), "Virtual environment not created correctly"