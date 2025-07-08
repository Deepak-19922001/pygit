#!/bin/bash

set -u
trap 'echo "FAIL: A command exited with an error. Test aborted."; exit 1' ERR

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
TEST_DIR="$SCRIPT_DIR/pygit_test_repo"
PYGIT_CMD="python3 $SCRIPT_DIR/pygit.py"

rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo -e "\n[TEST 1/8] pygit init"
$PYGIT_CMD init
if [ ! -d ".pygit" ]; then
    exit 1
fi

echo -e "\n[TEST 2/8] pygit add, commit, log"
echo "Hello, PyGit!" > file1.txt
$PYGIT_CMD add file1.txt
$PYGIT_CMD commit -m "Initial commit"
if ! $PYGIT_CMD log | grep -q "Initial commit"; then
    exit 1
fi
COMMIT1_HASH=$($PYGIT_CMD log | grep 'commit ' | head -n 1 | cut -d ' ' -f 2)

echo -e "\n[TEST 3/8] pygit status, diff"
echo "A new line." >> file1.txt
echo "untracked" > untracked.txt
if ! $PYGIT_CMD status | grep -q "modified:   file1.txt"; then
    exit 1
fi
if ! $PYGIT_CMD status | grep -q "untracked.txt"; then
    exit 1
fi
$PYGIT_CMD add file1.txt
STATUS_OUTPUT=$($PYGIT_CMD status)
if ! echo "$STATUS_OUTPUT" | awk '/Changes to be committed/{f=1;next} /Changes not staged for commit/{f=0} f' | grep -q "modified:   file1.txt"; then
    exit 1
fi
$PYGIT_CMD commit -m "Second commit"
COMMIT2_HASH=$($PYGIT_CMD log | grep 'commit ' | head -n 1 | cut -d ' ' -f 2)

echo -e "\n[TEST 4/8] pygit branch, checkout"
$PYGIT_CMD branch feature-branch $COMMIT1_HASH
$PYGIT_CMD checkout feature-branch
echo "feature" > feature-file.txt
$PYGIT_CMD add feature-file.txt
$PYGIT_CMD commit -m "Feature commit"
$PYGIT_CMD checkout main
if [ -f "feature-file.txt" ]; then
    exit 1
fi

echo -e "\n[TEST 5/8] pygit tag, detached HEAD"
$PYGIT_CMD checkout $COMMIT1_HASH
if ! $PYGIT_CMD status | grep -q "HEAD detached at"; then
    exit 1
fi
$PYGIT_CMD tag v1.0
$PYGIT_CMD checkout main
if ! $PYGIT_CMD tag | grep -q "v1.0"; then
    exit 1
fi

echo -e "\n[TEST 6/8] .gitignore"
echo "*.log" > .gitignore
echo "temp/" >> .gitignore
touch app.log
mkdir temp && touch temp/data.txt
if $PYGIT_CMD status | grep -q "app.log"; then
    exit 1
fi
if $PYGIT_CMD status | grep -q "temp/data.txt"; then
    exit 1
fi

echo -e "\n[TEST 7/8] pygit rm and merge"
$PYGIT_CMD add untracked.txt
$PYGIT_CMD commit -m "Add untracked.txt to track it"
$PYGIT_CMD rm untracked.txt
if [ -f "untracked.txt" ]; then
    exit 1
fi
STATUS_OUTPUT=$($PYGIT_CMD status)
if ! echo "$STATUS_OUTPUT" | awk '/Changes to be committed/{f=1;next} /Changes not staged for commit/{f=0} f' | grep -q "deleted:    untracked.txt"; then
    exit 1
fi
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
    exit 1
fi
$PYGIT_CMD branch ff-branch
$PYGIT_CMD checkout ff-branch
echo "ff" > ff.txt
$PYGIT_CMD add ff.txt
$PYGIT_CMD commit -m "Fast-forward commit"
FF_HASH=$($PYGIT_CMD log | grep 'commit ' | head -n 1 | cut -d ' ' -f 2)
$PYGIT_CMD checkout main
$PYGIT_CMD merge ff-branch
if ! $PYGIT_CMD log | grep -q "$FF_HASH"; then
    exit 1
fi

echo -e "\n[TEST 8/8] pygit stash"
echo "stashed content" > stash-test.txt
$PYGIT_CMD add stash-test.txt
echo "more stashed content" >> stash-test.txt
$PYGIT_CMD stash push
if ! grep -q "stashed content" stash-test.txt; then
    exit 1
fi
if ! $PYGIT_CMD stash list | grep -q "stash@{0}"; then
    exit 1
fi
$PYGIT_CMD stash pop
if ! grep -q "more stashed content" stash-test.txt; then
    exit 1
fi
if $PYGIT_CMD stash list | grep -q "stash@{0}"; then
    exit 1
fi

cd ..
rm -rf "$TEST_DIR"
echo -e "\n--- PyGit Test Suite Completed Successfully ---"
