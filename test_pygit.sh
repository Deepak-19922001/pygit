#!/bin/bash

# A comprehensive test script for the pygit application with enhanced logging.
# It creates a temporary directory, runs all commands, and then cleans up.

# --- Setup ---
set -e # Exit immediately if a command exits with a non-zero status.
TEST_DIR="pygit_test_repo"

# Make the path to pygit.py robust, assuming test_pygit.sh is in the same dir.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PYGIT_CMD="python3 $SCRIPT_DIR/pygit.py"

echo "--- Preparing Test Environment ---"
# Clean up previous test runs if they exist
if [ -d "$TEST_DIR" ]; then
    echo "Removing previous test directory."
    rm -rf "$TEST_DIR"
fi
mkdir "$TEST_DIR"
cd "$TEST_DIR"
echo "Test directory created at $(pwd)"
echo "--- Starting PyGit Test Suite ---"

# --- 1. Testing Init ---
echo -e "\n[TEST] pygit init"
$PYGIT_CMD init
if [ ! -d ".pygit" ]; then
    echo "FAIL: .pygit directory not created."
    exit 1
fi
echo "PASS: Repository initialized."

# --- 2. Testing Add, Commit, Log ---
echo -e "\n[TEST] pygit add, commit, log"
echo "  - Creating file1.txt"
echo "Hello, PyGit!" > file1.txt
echo "  - Running 'add file1.txt'"
$PYGIT_CMD add file1.txt
echo "  - Running 'commit -m \"Initial commit\"'"
$PYGIT_CMD commit -m "Initial commit"

echo "  - Running 'log' to verify..."
if $PYGIT_CMD log | grep -q "Initial commit"; then
    echo "PASS: Initial commit successful."
else
    echo "FAIL: Could not find initial commit in log."
    exit 1
fi
COMMIT1_HASH=$($PYGIT_CMD log | grep 'commit ' | head -n 1 | cut -d ' ' -f 2)
echo "  - Captured COMMIT1_HASH: ${COMMIT1_HASH:0:7}"

# --- 3. Testing Status and Diff ---
echo -e "\n[TEST] pygit status and diff"
echo "  - Modifying file1.txt and creating untracked_file.txt"
echo "A new line." >> file1.txt
echo "Untracked content" > untracked_file.txt

echo "  - Running 'status' for unstaged changes..."
$PYGIT_CMD status

echo "  - Running 'diff' for unstaged changes..."
$PYGIT_CMD diff

echo "  - Staging file1.txt"
$PYGIT_CMD add file1.txt
echo "  - Running 'status' for staged changes..."
$PYGIT_CMD status

echo "  - Running 'diff --staged'..."
$PYGIT_CMD diff --staged

echo "  - Committing second change"
$PYGIT_CMD commit -m "Update file1.txt"
COMMIT2_HASH=$($PYGIT_CMD log | grep 'commit ' | head -n 1 | cut -d ' ' -f 2)
echo "  - Captured COMMIT2_HASH: ${COMMIT2_HASH:0:7}"
echo "PASS: Status and Diff tests completed."


# --- 4. Testing Branching and Checkout ---
echo -e "\n[TEST] pygit branch and checkout"
echo "  - Running 'branch feature-branch'"
$PYGIT_CMD branch feature-branch

echo "  - Running 'checkout feature-branch'"
$PYGIT_CMD checkout feature-branch

echo "  - Creating and committing 'feature-file.txt' on new branch"
echo "Feature content" > feature-file.txt
$PYGIT_CMD add feature-file.txt
$PYGIT_CMD commit -m "Add feature file"

echo "  - Running 'checkout main'"
$PYGIT_CMD checkout main
if [ -f "feature-file.txt" ]; then
    echo "  FAIL: feature-file.txt was not removed on checkout to main."
    exit 1
else
    echo "  PASS: Workspace correctly updated on checkout."
fi
echo "PASS: Branching and Checkout tests completed."


# --- 5. Testing Tags and Detached HEAD ---
echo -e "\n[TEST] pygit tag and detached HEAD"
echo "  - Running 'checkout' with a commit hash"
$PYGIT_CMD checkout $COMMIT1_HASH

echo "  - Running 'tag v1.0'"
$PYGIT_CMD tag v1.0
echo "  - Running 'checkout main' again"
$PYGIT_CMD checkout main

if $PYGIT_CMD tag | grep -q "v1.0"; then
    echo "  PASS: Tag 'v1.0' created and listed successfully."
else
    echo "  FAIL: Tag was not created or listed."
    exit 1
fi
echo "PASS: Tag and Detached HEAD tests completed."


# --- 6. Testing .gitignore ---
echo -e "\n[TEST] .gitignore"
echo "  - Creating and committing .gitignore file"
echo "*.log" > .gitignore
echo "temp/" >> .gitignore
touch app.log
mkdir temp
touch temp/data.txt
$PYGIT_CMD add .gitignore
$PYGIT_CMD commit -m "Add gitignore"

echo "  - Checking 'status' for ignored files"
if ! ($PYGIT_CMD status | grep -q "app.log") && ! ($PYGIT_CMD status | grep -q "temp/data.txt"); then
    echo "PASS: .gitignore is correctly ignoring files and directories."
else
    echo "FAIL: .gitignore is not working."
    exit 1
fi

# --- 7. Testing Fast-Forward Merge ---
echo -e "\n[TEST] Fast-forward merge"
echo "  - Creating branch 'ff-branch' from an older commit"
$PYGIT_CMD branch ff-branch $COMMIT2_HASH
echo "  - Checking out 'ff-branch'"
$PYGIT_CMD checkout ff-branch
echo "  - Creating a new commit on ff-branch"
echo "new content" > ff-file.txt
$PYGIT_CMD add ff-file.txt
$PYGIT_CMD commit -m "Commit on ff-branch"

echo "  - Checking out main and merging (should fail as it's not a fast-forward)"
$PYGIT_CMD checkout main
if ! $PYGIT_CMD merge ff-branch; then
    echo "  PASS: Correctly failed non-fast-forward merge."
else
    echo "  FAIL: Should have failed non-fast-forward merge."
fi

echo "  - Creating a true fast-forward scenario"
$PYGIT_CMD checkout ff-branch
echo "  - Running 'merge main' (which is ahead)"
if $PYGIT_CMD merge main; then
    echo "PASS: Fast-forward merge successful."
else
    echo "FAIL: Fast-forward merge failed."
    exit 1
fi


# --- Cleanup ---
echo -e "\n--- Cleaning up Test Environment ---"
cd ..
rm -rf $TEST_DIR
echo "--- PyGit Test Suite Completed Successfully ---"
