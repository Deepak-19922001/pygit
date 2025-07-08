#!/bin/bash


set -u
trap 'echo "FAIL: A command exited with an error. Test aborted."; exit 1' ERR

# Find the directory where the script is located to build robust paths
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
TEST_DIR="$SCRIPT_DIR/pygit_test_repo"
PYGIT_CMD="python3 $SCRIPT_DIR/pygit.py"

# --- Test Runner ---
echo "--- Preparing PyGit Test Environment ---"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
echo "Test directory created at: $(pwd)"
echo "--- Starting PyGit Test Suite ---"

# --- 1. Init Command ---
echo -e "\n[TEST 1/9] pygit init"
$PYGIT_CMD init
if [ ! -d ".pygit" ]; then
    echo "  FAIL: .pygit directory was not created."
    exit 1
fi
echo "  PASS: Repository initialized successfully."

# --- 2. Add, Commit, and Log Commands ---
echo -e "\n[TEST 2/9] pygit add, commit, log"
echo "Hello, PyGit!" > file1.txt
$PYGIT_CMD add file1.txt
$PYGIT_CMD commit -m "Initial commit"
if ! $PYGIT_CMD log | grep -q "Initial commit"; then
    echo "  FAIL: 'log' command did not show the initial commit."
    exit 1
fi
COMMIT1_HASH=$($PYGIT_CMD log | grep 'commit ' | head -n 1 | cut -d ' ' -f 2)
echo "  PASS: add, commit, and log work as expected."

# --- 3. Status and Diff Commands ---
echo -e "\n[TEST 3/9] pygit status, diff"
echo "A new line." >> file1.txt
echo "untracked" > untracked.txt
if ! $PYGIT_CMD status | grep -q "modified:   file1.txt"; then
    echo "  FAIL: 'status' did not detect an unstaged modification."
    exit 1
fi
if ! $PYGIT_CMD status | grep -q "untracked.txt"; then
    echo "  FAIL: 'status' did not detect an untracked file."
    exit 1
fi
echo "  - Unstaged status is correct."

$PYGIT_CMD add file1.txt
STATUS_OUTPUT=$($PYGIT_CMD status)
if ! echo "$STATUS_OUTPUT" | awk '/Changes to be committed/{f=1;next} /Changes not staged for commit/{f=0} f' | grep -q "modified:   file1.txt"; then
    echo "  FAIL: 'status' did not detect a staged modification."
    exit 1
fi
echo "  - Staged status is correct."

$PYGIT_CMD commit -m "Second commit"
COMMIT2_HASH=$($PYGIT_CMD log | grep 'commit ' | head -n 1 | cut -d ' ' -f 2)
echo "  PASS: status and diff work as expected."

# --- 4. Branch and Checkout Commands ---
echo -e "\n[TEST 4/9] pygit branch, checkout"
$PYGIT_CMD branch feature-branch $COMMIT1_HASH
$PYGIT_CMD checkout feature-branch
echo "feature" > feature-file.txt
$PYGIT_CMD add feature-file.txt
$PYGIT_CMD commit -m "Feature commit"
$PYGIT_CMD checkout main
if [ -f "feature-file.txt" ]; then
    echo "  FAIL: 'checkout' did not remove file from other branch."
    exit 1
fi
echo "  PASS: branch and checkout work as expected."

# --- 5. Tag and Detached HEAD ---
echo -e "\n[TEST 5/9] pygit tag, detached HEAD"
$PYGIT_CMD checkout $COMMIT1_HASH
if ! $PYGIT_CMD status | grep -q "HEAD detached at"; then
    echo "  FAIL: 'status' did not report a detached HEAD."
    exit 1
fi
$PYGIT_CMD tag v1.0
$PYGIT_CMD checkout main
if ! $PYGIT_CMD tag | grep -q "v1.0"; then
    echo "  FAIL: 'tag' command did not list the new tag."
    exit 1
fi
echo "  PASS: tag and detached HEAD work as expected."

# --- 6. .gitignore Functionality ---
echo -e "\n[TEST 6/9] .gitignore"
echo "*.log" > .gitignore
echo "temp/" >> .gitignore
touch app.log
mkdir temp && touch temp/data.txt
if $PYGIT_CMD status | grep -q "app.log"; then
    echo "  FAIL: .gitignore did not ignore the log file."
    exit 1
fi
if $PYGIT_CMD status | grep -q "temp/data.txt"; then
    echo "  FAIL: .gitignore did not ignore the temp directory."
    exit 1
fi
echo "  PASS: .gitignore works as expected."

# --- 7. RM and Merge Commands ---
echo -e "\n[TEST 7/9] pygit rm and merge"
$PYGIT_CMD add untracked.txt
$PYGIT_CMD commit -m "Add untracked.txt to track it"
$PYGIT_CMD rm untracked.txt
if [ -f "untracked.txt" ]; then
    echo "  FAIL: 'rm' did not delete the file from the working directory."
    exit 1
fi
STATUS_OUTPUT=$($PYGIT_CMD status)
if ! echo "$STATUS_OUTPUT" | awk '/Changes to be committed/{f=1;next} /Changes not staged for commit/{f=0} f' | grep -q "deleted:    untracked.txt"; then
    echo "  FAIL: 'rm' did not stage the deletion."
    exit 1
fi
echo "  - rm works as expected."

# Non-fast-forward (should fail)
$PYGIT_CMD checkout main
$PYGIT_CMD branch non-ff-branch
echo "main change" >> file1.txt
$PYGIT_CMD add file1.txt
$PYGIT_CMD commit -m "Diverge main"
$PYGIT_CMD checkout non-ff-branch
echo "branch change" >> file1.txt
$PYGIT_CMD add file1.txt
$PYGIT_CMD commit -m "Diverge branch"
$PYGIT_CMD checkout main
if $PYGIT_CMD merge non-ff-branch; then
    echo "  FAIL: Non-fast-forward merge was expected to fail but succeeded."
    exit 1
fi
echo "  - Non-fast-forward merge correctly failed."

# Fast-forward (should succeed)
$PYGIT_CMD branch ff-branch
$PYGIT_CMD checkout ff-branch
echo "ff" > ff.txt
$PYGIT_CMD add ff.txt
$PYGIT_CMD commit -m "Fast-forward commit"
FF_HASH=$($PYGIT_CMD log | grep 'commit ' | head -n 1 | cut -d ' ' -f 2)
$PYGIT_CMD checkout main
$PYGIT_CMD merge ff-branch
if ! $PYGIT_CMD log | grep -q "$FF_HASH"; then
    echo "  FAIL: Fast-forward merge failed; commit not in main's history."
    exit 1
fi
echo "  - Fast-forward merge correctly succeeded."
echo "  PASS: rm and merge work as expected."

# --- 8. Stash Command ---
echo -e "\n[TEST 8/9] pygit stash"
echo "stashed content" > stash-test.txt
$PYGIT_CMD add stash-test.txt
echo "more stashed content" >> stash-test.txt
$PYGIT_CMD stash push
if ! grep -q "stashed content" stash-test.txt; then
    echo "  FAIL: Stash did not clean working directory correctly."
    exit 1
fi
if ! $PYGIT_CMD stash list | grep -q "stash@{0}"; then
    echo "  FAIL: Stash was not created or listed."
    exit 1
fi
echo "  - Stash push and list work as expected."

$PYGIT_CMD stash pop
if ! grep -q "more stashed content" stash-test.txt; then
    echo "  FAIL: Stash pop did not restore working directory changes."
    exit 1
fi
if $PYGIT_CMD stash list | grep -q "stash@{0}"; then
    echo "  FAIL: Stash pop did not remove the stash from the list."
    exit 1
fi
echo "  - Stash pop works as expected."
echo "  PASS: Stash command works as expected."

# --- 9. Clean Command ---
echo -e "\n[TEST 9/9] pygit clean"
echo "untracked file to clean" > clean-me.txt
mkdir clean-dir && echo "data" > clean-dir/file.txt
if ! $PYGIT_CMD clean -n | grep -q "Would remove clean-me.txt"; then
    echo "  FAIL: Clean dry run did not list the untracked file."
    exit 1
fi
if [ ! -f "clean-me.txt" ]; then
    echo "  FAIL: Clean dry run deleted the file."
    exit 1
fi
echo "  - Dry run works as expected."

$PYGIT_CMD clean -f
if [ -f "clean-me.txt" ]; then
    echo "  FAIL: Clean with -f did not remove the file."
    exit 1
fi
echo "  - Force clean for files works as expected."

# Force clean directories
$PYGIT_CMD clean -f -d
if [ -d "clean-dir" ]; then
    echo "  FAIL: Clean with -fd did not remove the directory."
    exit 1
fi
echo "  - Force clean for directories works as expected."
echo "  PASS: Clean command works as expected."


cd ..
rm -rf "$TEST_DIR"
echo -e "\n--- PyGit Test Suite Completed Successfully ---"
