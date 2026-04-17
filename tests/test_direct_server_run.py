# tests/test_direct_server_run.py

import subprocess

def test_direct_server_run():
    # Navigate to the project directory
    project_dir = os.path.join(os.getcwd(), "..")

    # Activate the virtual environment and run the server
    activate_script = os.path.join(project_dir, "venv", "bin", "activate")
    pip_path = os.path.join(project_dir, "venv", "bin", "pip")
    requirements_path = os.path.join(project_dir, "requirements.txt")
    server_script = os.path.join(project_dir, "agent_server.py")

    # Install dependencies
    subprocess.run([pip_path, "install", "-r", requirements_path], check=True)

    # Run the server
    result = subprocess.run(["python", server_script], cwd=project_dir, capture_output=True, text=True)
    assert "Server started" in result.stdout, "Server not started correctly"