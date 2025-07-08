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
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        # Get the path to the pygit.py script
        script_dir = Path(__file__).parent.absolute()
        self.pygit_cmd = f"python3 {script_dir}/pygit.py"

    def tearDown(self):
        """Clean up after tests."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def run_command(self, command):
        """Run a pygit command and return its output."""
        full_command = f"{self.pygit_cmd} {command}"
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
        if result.returncode != 0 and not command.startswith("merge") and "clean -n" not in command:
            # We expect merge to fail in conflict test, and clean -n is just a dry run
            self.fail(f"Command '{full_command}' failed with error: {result.stderr}")
        return result.stdout, result.stderr, result.returncode

    def test_01_init(self):
        """Test the init command."""
        self.run_command("init")
        self.assertTrue(os.path.isdir(".pygit"), "The .pygit directory was not created")

    def test_02_add_commit_log(self):
        """Test the add, commit, and log commands."""
        self.run_command("init")
        
        # Create a file and add it
        with open("file1.txt", "w") as f:
            f.write("Hello, PyGit!")
        
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")
        
        # Check if the commit is in the log
        stdout, _, _ = self.run_command("log")
        self.assertIn("Initial commit", stdout, "Log did not show the initial commit")

    def test_03_status_diff(self):
        """Test the status and diff commands."""
        self.run_command("init")
        
        # Create a file, add it, and commit it
        with open("file1.txt", "w") as f:
            f.write("Hello, PyGit!")
        
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")
        
        # Modify the file and create an untracked file
        with open("file1.txt", "a") as f:
            f.write("\nA new line.")
        
        with open("untracked.txt", "w") as f:
            f.write("untracked")
        
        # Check status for unstaged changes
        stdout, _, _ = self.run_command("status")
        self.assertIn("modified:   file1.txt", stdout, "Status did not detect an unstaged modification")
        self.assertIn("untracked.txt", stdout, "Status did not detect an untracked file")
        
        # Add the modified file and check status for staged changes
        self.run_command("add file1.txt")
        stdout, _, _ = self.run_command("status")
        self.assertIn("modified:   file1.txt", stdout, "Status did not detect a staged modification")
        
        # Commit the changes
        self.run_command("commit -m \"Second commit\"")

    def test_04_branch_checkout(self):
        """Test the branch and checkout commands."""
        self.run_command("init")
        
        # Create a file, add it, and commit it
        with open("file1.txt", "w") as f:
            f.write("Hello, PyGit!")
        
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")
        
        # Get the commit hash
        stdout, _, _ = self.run_command("log")
        commit_hash = None
        for line in stdout.splitlines():
            if line.startswith("commit "):
                commit_hash = line.split()[1]
                break
        
        self.assertIsNotNone(commit_hash, "Could not find commit hash in log")
        
        # Create a branch and switch to it
        self.run_command(f"branch feature-branch {commit_hash}")
        self.run_command("checkout feature-branch")
        
        # Create a file on the feature branch
        with open("feature-file.txt", "w") as f:
            f.write("feature")
        
        self.run_command("add feature-file.txt")
        self.run_command("commit -m \"Feature commit\"")
        
        # Switch back to main branch
        self.run_command("checkout main")
        
        # Check that the feature file is not present
        self.assertFalse(os.path.exists("feature-file.txt"), "Checkout did not remove file from other branch")

    def test_05_tag_detached_head(self):
        """Test the tag command and detached HEAD state."""
        self.run_command("init")
        
        # Create a file, add it, and commit it
        with open("file1.txt", "w") as f:
            f.write("Hello, PyGit!")
        
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")
        
        # Get the commit hash
        stdout, _, _ = self.run_command("log")
        commit_hash = None
        for line in stdout.splitlines():
            if line.startswith("commit "):
                commit_hash = line.split()[1]
                break
        
        self.assertIsNotNone(commit_hash, "Could not find commit hash in log")
        
        # Checkout the commit directly (detached HEAD)
        self.run_command(f"checkout {commit_hash}")
        
        # Check if we're in detached HEAD state
        stdout, _, _ = self.run_command("status")
        self.assertIn("HEAD detached at", stdout, "Status did not report a detached HEAD")
        
        # Create a tag and check if it exists
        self.run_command("tag v1.0")
        self.run_command("checkout main")
        stdout, _, _ = self.run_command("tag")
        self.assertIn("v1.0", stdout, "Tag command did not list the new tag")

    def test_06_gitignore(self):
        """Test .gitignore functionality."""
        self.run_command("init")
        
        # Create a .gitignore file
        with open(".gitignore", "w") as f:
            f.write("*.log\n")
            f.write("temp/\n")
        
        # Create files that should be ignored
        with open("app.log", "w") as f:
            f.write("log data")
        
        os.makedirs("temp", exist_ok=True)
        with open("temp/data.txt", "w") as f:
            f.write("temp data")
        
        # Check if the files are ignored
        stdout, _, _ = self.run_command("status")
        self.assertNotIn("app.log", stdout, ".gitignore did not ignore the log file")
        self.assertNotIn("temp/data.txt", stdout, ".gitignore did not ignore the temp directory")

    def test_07_rm(self):
        """Test the rm command."""
        self.run_command("init")
        
        # Create a file, add it, and commit it
        with open("file1.txt", "w") as f:
            f.write("Hello, PyGit!")
        
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")
        
        # Remove the file
        self.run_command("rm file1.txt")
        
        # Check if the file is removed from the filesystem
        self.assertFalse(os.path.exists("file1.txt"), "rm did not delete the file from the working directory")
        
        # Check if the deletion is staged
        stdout, _, _ = self.run_command("status")
        self.assertIn("deleted:    file1.txt", stdout, "rm did not stage the deletion")

    def test_08_stash(self):
        """Test the stash command."""
        self.run_command("init")
        
        # Create a file, add it, and commit it
        with open("file1.txt", "w") as f:
            f.write("Hello, PyGit!")
        
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")
        
        # Create a new file for stashing
        with open("stash-test.txt", "w") as f:
            f.write("stashed content")
        
        self.run_command("add stash-test.txt")
        
        # Modify the file after adding
        with open("stash-test.txt", "a") as f:
            f.write("\nmore stashed content")
        
        # Stash the changes
        self.run_command("stash push")
        
        # Check if the file is back to its original state
        with open("stash-test.txt", "r") as f:
            content = f.read()
        self.assertEqual(content, "stashed content", "Stash did not clean working directory correctly")
        
        # Check if the stash is listed
        stdout, _, _ = self.run_command("stash list")
        self.assertIn("stash@{0}", stdout, "Stash was not created or listed")
        
        # Pop the stash
        self.run_command("stash pop")
        
        # Check if the changes are restored
        with open("stash-test.txt", "r") as f:
            content = f.read()
        self.assertIn("more stashed content", content, "Stash pop did not restore working directory changes")
        
        # Check if the stash is removed from the list
        stdout, _, _ = self.run_command("stash list")
        self.assertNotIn("stash@{0}", stdout, "Stash pop did not remove the stash from the list")

    def test_09_clean(self):
        """Test the clean command."""
        self.run_command("init")
        
        # Create untracked files and directories
        with open("clean-me.txt", "w") as f:
            f.write("untracked file to clean")
        
        os.makedirs("clean-dir", exist_ok=True)
        with open("clean-dir/file.txt", "w") as f:
            f.write("data")
        
        # Test dry run
        stdout, _, _ = self.run_command("clean -n")
        self.assertIn("Would remove clean-me.txt", stdout, "Clean dry run did not list the untracked file")
        self.assertTrue(os.path.exists("clean-me.txt"), "Clean dry run deleted the file")
        
        # Test force clean for files
        self.run_command("clean -f")
        self.assertFalse(os.path.exists("clean-me.txt"), "Clean with -f did not remove the file")
        
        # Test force clean for directories
        self.run_command("clean -f -d")
        self.assertFalse(os.path.exists("clean-dir"), "Clean with -fd did not remove the directory")

    def test_10_config(self):
        """Test the config command."""
        self.run_command("init")
        
        # Set and get config values
        self.run_command("config user.name \"Test User\"")
        self.run_command("config user.email \"test@example.com\"")
        
        stdout, _, _ = self.run_command("config user.name")
        self.assertIn("Test User", stdout, "Config did not get user.name correctly")
        
        # Create a commit and check if it uses the configured user
        with open("file1.txt", "w") as f:
            f.write("Hello, PyGit!")
        
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Config test commit\"")
        
        stdout, _, _ = self.run_command("log")
        self.assertIn("Author: Test User <test@example.com>", stdout, "Commit did not use configured author")

    def test_11_merge(self):
        """Test the merge command."""
        self.run_command("init")
        
        # Create a file, add it, and commit it
        with open("file1.txt", "w") as f:
            f.write("Hello, PyGit!")
        
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")
        
        # Get the commit hash
        stdout, _, _ = self.run_command("log")
        commit_hash = None
        for line in stdout.splitlines():
            if line.startswith("commit "):
                commit_hash = line.split()[1]
                break
        
        self.assertIsNotNone(commit_hash, "Could not find commit hash in log")
        
        # Create two branches from the initial commit
        self.run_command(f"checkout {commit_hash}")
        self.run_command("branch branch1")
        self.run_command("branch branch2")
        
        # Make changes on branch1
        self.run_command("checkout branch1")
        with open("b1.txt", "w") as f:
            f.write("b1")
        
        self.run_command("add b1.txt")
        self.run_command("commit -m \"Commit on branch1\"")
        
        # Make changes on branch2
        self.run_command("checkout branch2")
        with open("b2.txt", "w") as f:
            f.write("b2")
        
        self.run_command("add b2.txt")
        self.run_command("commit -m \"Commit on branch2\"")
        
        # Merge branch2 into branch1
        self.run_command("checkout branch1")
        self.run_command("merge branch2")
        
        # Check if both files exist after merge
        self.assertTrue(os.path.exists("b1.txt"), "Successful merge did not contain file from branch1")
        self.assertTrue(os.path.exists("b2.txt"), "Successful merge did not contain file from branch2")
        
        # Test merge conflict
        # Create a conflict file on branch1
        with open("conflict.txt", "w") as f:
            f.write("conflict1")
        
        self.run_command("add conflict.txt")
        self.run_command("commit -m \"Ready for conflict on branch1\"")
        
        # Create the same file with different content on branch2
        self.run_command("checkout branch2")
        with open("conflict.txt", "w") as f:
            f.write("conflict2")
        
        self.run_command("add conflict.txt")
        self.run_command("commit -m \"Create conflict on branch2\"")
        
        # Try to merge branch2 into branch1 (should fail with conflict)
        self.run_command("checkout branch1")
        _, _, returncode = self.run_command("merge branch2")
        
        # Check if the merge failed and conflict markers are present
        self.assertNotEqual(returncode, 0, "Conflicting merge was expected to fail but succeeded")
        
        with open("conflict.txt", "r") as f:
            content = f.read()
        self.assertIn("<<<<<<< HEAD", content, "Conflict markers not found in conflicted file")

    def test_12_show_and_annotated_tags(self):
        """Test the show command and annotated tags."""
        self.run_command("init")
        
        # Create a file, add it, and commit it
        with open("file1.txt", "w") as f:
            f.write("Hello, PyGit!")
        
        self.run_command("add file1.txt")
        self.run_command("commit -m \"Initial commit\"")
        
        # Test show HEAD
        stdout, _, _ = self.run_command("show HEAD")
        self.assertIn("Initial commit", stdout, "show HEAD did not display the latest commit")
        
        # Create an annotated tag
        self.run_command("tag -m \"Annotated v1.1\" v1.1")
        
        # Test show tag
        stdout, _, _ = self.run_command("show v1.1")
        self.assertIn("Annotated v1.1", stdout, "show did not display the annotated tag's message")
        self.assertIn("tagger", stdout, "show did not display the tagger for the annotated tag")


if __name__ == "__main__":
    unittest.main()