# tests/test_clone_and_navigate.py

import os
import subprocess

def test_clone_and_navigate():
    # Clone the repository
    repo_url = "https://github.com/username/repository.git"
    project_dir = os.path.join(os.getcwd(), "..", "mini_ki_tools")

    # Check if the project directory already exists
    assert not os.path.exists(project_dir), "Project directory already exists"

    # Clone the repository
    subprocess.run(["git", "clone", repo_url, project_dir], check=True)

    # Verify that the repository was cloned successfully
    assert os.path.exists(os.path.join(project_dir, ".git")), "Repository not cloned correctly"