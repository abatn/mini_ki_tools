# tests/test_docker_build_and_run.py

import subprocess

def test_docker_build_and_run():
    # Navigate to the project directory
    project_dir = os.path.join(os.getcwd(), "..")

    # Build the Docker image
    dockerfile_path = os.path.join(project_dir, "Dockerfile")
    subprocess.run(["docker", "build", "-t", "local-agent", "."], cwd=project_dir, check=True)

    # Verify that the Docker image was built successfully
    result = subprocess.run(["docker", "images"], capture_output=True, text=True)
    assert "local-agent" in result.stdout, "Docker image not built correctly"

    # Run the Docker container
    subprocess.run(["docker", "run", "-p", "8000:8000", "local-agent"], cwd=project_dir, check=True)

    # Verify that the container is running
    result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
    assert "local-agent" in result.stdout, "Docker container not running correctly"