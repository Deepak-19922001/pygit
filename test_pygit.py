import os
import sys
import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path


class PyGitTest(unittest.TestCase):
    """Test suite for PyGit functionality."""

    def setUp(self):
        """Set up a temporary directory for testing."""
        # Create a main directory for the test run to contain both client and server repos
        self.base_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.base_dir)

        # The actual test repo will be inside the base_dir
        self.test_dir = os.path.join(self.base_dir, "test_repo")
        os.makedirs(self.test_dir)
        os.chdir(self.test_dir)

        # Get the absolute path to the pygit.py script
        # Assumes the test script is run from the project root
        script_dir = Path(self.original_dir).absolute()
        self.pygit_cmd = f"python3 {script_dir}/pygit.py"

    def tearDown(self):
        """Clean up after tests."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.base_dir)

    def run_command(self, command, expect_fail=False):
        """Run a pygit command and return its output and return code."""
        full_command = f"{self.pygit_cmd} {command}"
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
        if not expect_fail and result.returncode != 0:
            self.fail(f"Command '{full_command}' failed with error:\n{result.stderr}")
        elif expect_fail and result.returncode == 0:
            self.fail(f"Command '{full_command}' was expected to fail but succeeded.")
        return result.stdout, result.stderr, result.returncode

    def test_01_init(self):
        """Test the init command."""
        self.run_command("init")
        self.assertTrue(os.path.isdir(".pygit"), "The .pygit directory was not created")

    def test_02_add_commit_log(self):
        """Test the add, commit, and log commands."""
        self.run_command("init")
        with open("file1.txt", "w") as f: f.write("Hello, PyGit!")
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")
        stdout, _, _ = self.run_command("log")
        self.assertIn("Initial commit", stdout, "Log did not show the initial commit")

    def test_03_status_diff(self):
        """Test the status and diff commands."""
        self.run_command("init")
        with open("file1.txt", "w") as f: f.write("content")
        self.run_command("add file1.txt")
        self.run_command("commit -m \"commit 1\"")

        with open("file1.txt", "a") as f: f.write("\nmore content")
        with open("untracked.txt", "w") as f: f.write("untracked")

        stdout, _, _ = self.run_command("status")
        self.assertIn("modified:   file1.txt", stdout)
        self.assertIn("untracked.txt", stdout)

        self.run_command("add file1.txt")
        stdout, _, _ = self.run_command("status")
        self.assertIn("Changes to be committed", stdout)
        self.assertIn("modified:   file1.txt", stdout)

    def test_04_branch_checkout(self):
        """Test the branch and checkout commands."""
        self.run_command("init")
        with open("file1.txt", "w") as f: f.write("content")
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")

        self.run_command("branch feature-branch")
        self.run_command("checkout feature-branch")
        with open("feature-file.txt", "w") as f: f.write("feature")
        self.run_command("add feature-file.txt")
        self.run_command("commit -m \"Feature commit\"")

        self.run_command("checkout main")
        self.assertFalse(os.path.exists("feature-file.txt"))

    def test_05_tag_and_show(self):
        """Test tag (lightweight and annotated) and show commands."""
        self.run_command("init")
        with open("file1.txt", "w") as f: f.write("content")
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")

        stdout, _, _ = self.run_command("log")
        commit_hash = stdout.split()[1]

        # Lightweight tag
        self.run_command("tag v1.0")
        stdout, _, _ = self.run_command("tag")
        self.assertIn("v1.0", stdout)

        # Annotated tag
        self.run_command("tag -m \"Release v1.1\" v1.1")
        stdout, _, _ = self.run_command("show v1.1")
        self.assertIn("Release v1.1", stdout)
        self.assertIn("tagger", stdout)

        # Show commit
        stdout, _, _ = self.run_command(f"show {commit_hash}")
        self.assertIn("Initial commit", stdout)

    def test_06_remote_and_clone(self):
        """Test remote and clone commands."""
        # Setup a "server" repo
        server_path = os.path.join(self.base_dir, "server.git")
        os.makedirs(server_path)
        os.chdir(server_path)
        self.run_command("init")
        with open("server_file.txt", "w") as f: f.write("server content")
        self.run_command("add server_file.txt")
        self.run_command("commit -m \"Initial server commit\"")
        os.chdir(self.base_dir)

        # Clone it
        self.run_command(f"clone {server_path} client_repo")
        os.chdir("client_repo")
        self.assertTrue(os.path.isdir(".pygit"))

        # Check remote
        stdout, _, _ = self.run_command("remote")
        self.assertIn("origin", stdout)

        # Test remote add/remove
        self.run_command(f"remote add test_remote {server_path}")
        stdout, _, _ = self.run_command("remote")
        self.assertIn("test_remote", stdout)
        self.run_command("remote remove test_remote")
        stdout, _, _ = self.run_command("remote")
        self.assertNotIn("test_remote", stdout)


if __name__ == "__main__":
    unittest.main()
