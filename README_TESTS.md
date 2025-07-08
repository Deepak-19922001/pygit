# PyGit Test Suite

This directory contains a comprehensive test suite for the PyGit project. The tests are written in Python using the unittest framework and cover all the major functionality of PyGit.

## Test Files

- `test_pygit.py`: Contains the main test suite with 12 test methods that test different aspects of PyGit.
- `run_tests.py`: A simple script to run all the tests and display the results.

## Running the Tests

You can run the tests in two ways:

### Option 1: Using run_tests.py

```bash
python3 run_tests.py
```

This will run all the tests and display a summary of the results.

### Option 2: Using unittest directly

```bash
python3 -m unittest test_pygit.py
```

## What the Tests Cover

The test suite covers the following functionality:

1. **Repository Initialization**: Tests the `init` command to create a new repository.
2. **Add, Commit, and Log**: Tests adding files to the staging area, committing changes, and viewing the commit history.
3. **Status and Diff**: Tests checking the status of the repository and viewing differences between commits.
4. **Branch and Checkout**: Tests creating branches and switching between them.
5. **Tag and Detached HEAD**: Tests creating tags and working with a detached HEAD.
6. **.gitignore Functionality**: Tests that files specified in .gitignore are properly ignored.
7. **Remove Command**: Tests removing files from the repository.
8. **Stash Command**: Tests stashing changes, listing stashes, and applying stashed changes.
9. **Clean Command**: Tests removing untracked files and directories.
10. **Config Command**: Tests setting and getting configuration values.
11. **Merge Command**: Tests merging branches, including handling conflicts.
12. **Show and Annotated Tags**: Tests showing objects and working with annotated tags.

## Test Environment

The tests create a temporary directory for testing and clean up after themselves. Each test is isolated from the others to ensure reliable results.

## Extending the Tests

If you want to add more tests, you can add new test methods to the `PyGitTest` class in `test_pygit.py`. Make sure to follow the naming convention `test_XX_description` where `XX` is a number that determines the order in which the tests are run.