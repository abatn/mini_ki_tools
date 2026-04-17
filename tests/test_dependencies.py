# tests/test_dependencies.py

import subprocess

def test_install_dependencies():
    # Navigate to the project directory
    project_dir = os.path.join(os.getcwd(), "..")

    # Install dependencies using setup.sh
    subprocess.run([os.path.join(project_dir, "setup.sh")], check=True)

    # Verify that the dependencies were installed successfully
    pip_path = os.path.join(project_dir, "venv", "bin", "pip")
    result = subprocess.run([pip_path, "list"], capture_output=True, text=True)
    assert "some-dependency" in result.stdout, "Dependency not installed correctly"