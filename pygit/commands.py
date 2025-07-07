import os
import sys
import collections
from datetime import datetime
import json
from .repository import find_pygit_dir, init as repo_init
from .objects import read_object, hash_object, get_commit_tree, get_tree_contents
from .index import read_index, write_index
from .refs import get_head_ref, get_head_commit, update_head

def init():
    repo_init()


def add(filepath):
    if not os.path.exists(filepath):
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        return
    with open(filepath, 'rb') as f:
        content = f.read()

    sha1 = hash_object(content, 'blob')
    if not sha1: return

    index = read_index()
    index[filepath] = sha1
    write_index(index)

    print(f"Staged '{filepath}' for commit.")


def commit(*args):
    if not args or args[0] != '-m' or len(args) < 2:
        print("Usage: pygit commit -m <message>", file=sys.stderr)
        return
    message = args[1]

    index = read_index()
    if not index:
        print("Nothing to commit, staging area is empty.")
        return

    tree_data = json.dumps(index, sort_keys=True).encode()
    tree_sha1 = hash_object(tree_data, 'tree')

    parent_sha1 = get_head_commit()

    commit_data = (
        f"tree {tree_sha1}\n"
        f"parent {parent_sha1}\n"
        f"author PyGit User <user@pygit.com> {datetime.now().isoformat()}\n"
        f"committer PyGit User <user@pygit.com> {datetime.now().isoformat()}\n"
        f"\n"
        f"{message}\n"
    ).encode()

    commit_sha1 = hash_object(commit_data, 'commit')

    pygit_dir = find_pygit_dir()
    head_ref_path = get_head_ref()
    ref_full_path = os.path.join(pygit_dir, head_ref_path)

    os.makedirs(os.path.dirname(ref_full_path), exist_ok=True)
    with open(ref_full_path, 'w') as f:
        f.write(commit_sha1)

    write_index({})  # Clear the index
    print(f"Committed, commit hash: {commit_sha1}")


def log():
    commit_sha1 = get_head_commit()
    if not commit_sha1:
        print("No commits yet.")
        return

    while commit_sha1:
        print(f"commit {commit_sha1}")

        _, content = read_object(commit_sha1)
        commit_content = content.decode()

        lines = commit_content.split('\n')
        parent_line = next((line for line in lines if line.startswith('parent ')), None)
        author_line = next(line for line in lines if line.startswith('author '))
        print(f"Author: {author_line.split(' ', 1)[1]}")

        message_start_index = commit_content.find('\n\n') + 2
        print(f"\n    {commit_content[message_start_index:].strip()}\n")

        if parent_line and parent_line.split(' ')[1] != 'None':
            commit_sha1 = parent_line.split(' ')[1]
        else:
            commit_sha1 = None


def status():
    head_commit = get_head_commit()
    head_tree_sha = get_commit_tree(head_commit)
    head_tree = get_tree_contents(head_tree_sha)
    index = read_index()

    staged_changes = {
        'added': [f for f in index if f not in head_tree],
        'modified': [f for f in index if f in head_tree and index[f] != head_tree[f]],
        'deleted': [f for f in head_tree if f not in index]
    }
    print("Changes to be committed:")
    if not any(staged_changes.values()): print("  (no changes staged)")
    for f in staged_changes['added']: print(f"  new file:   {f}")
    for f in staged_changes['modified']: print(f"  modified:   {f}")
    for f in staged_changes['deleted']: print(f"  deleted:    {f}")
    print()

    unstaged_changes = collections.defaultdict(list)
    untracked_files = []
    all_tracked_files = set(index.keys()) | set(head_tree.keys())

    for root, _, files in os.walk('.'):
        if find_pygit_dir().split('/')[-1] in root: continue
        for filename in files:
            filepath = os.path.relpath(os.path.join(root, filename), '.')
            if filepath not in all_tracked_files:
                untracked_files.append(filepath)
                continue
            if filepath not in index:
                unstaged_changes['deleted'].append(filepath)
                continue
            with open(filepath, 'rb') as f:
                sha1 = hash_object(f.read(), 'blob')
            if sha1 != index[filepath]:
                unstaged_changes['modified'].append(filepath)

    print("Changes not staged for commit:")
    if not any(unstaged_changes.values()): print("  (use 'pygit add <file>...' to stage changes)")
    for f in unstaged_changes['modified']: print(f"  modified:   {f}")
    for f in unstaged_changes['deleted']: print(f"  deleted:    {f}")
    print()

    print("Untracked files:")
    if not untracked_files: print("  (no untracked files present)")
    for f in untracked_files: print(f"  {f}")


def branch(branch_name=None):
    pygit_dir = find_pygit_dir()
    heads_dir = os.path.join(pygit_dir, 'refs', 'heads')
    current_branch = get_head_ref().split('/')[-1]

    if not branch_name:
        branches = os.listdir(heads_dir)
        for b in sorted(branches):
            if b == current_branch:
                print(f"* {b}")
            else:
                print(f"  {b}")
        return

    new_branch_path = os.path.join(heads_dir, branch_name)
    if os.path.exists(new_branch_path):
        print(f"Error: branch '{branch_name}' already exists.", file=sys.stderr)
        return

    head_commit = get_head_commit()
    if not head_commit:
        print("Error: Cannot create branch from an empty repository.", file=sys.stderr)
        return

    with open(new_branch_path, 'w') as f:
        f.write(head_commit)
    print(f"Branch '{branch_name}' created.")


def checkout(name):
    pygit_dir = find_pygit_dir()
    branch_path = os.path.join(pygit_dir, 'refs', 'heads', name)
    if not os.path.exists(branch_path):
        print(f"Error: branch '{name}' not found.", file=sys.stderr)
        return

    update_head(f'refs/heads/{name}')

    with open(branch_path, 'r') as f:
        commit_sha1 = f.read().strip()

    tree_sha1 = get_commit_tree(commit_sha1)
    tree_contents = get_tree_contents(tree_sha1)

    write_index(tree_contents)

    index = read_index()
    workdir_files = set()
    for root, _, files in os.walk('.'):
        if find_pygit_dir().split('/')[-1] in root: continue
        for filename in files:
            filepath = os.path.relpath(os.path.join(root, filename), '.')
            workdir_files.add(filepath)

    for filepath in workdir_files - set(index.keys()):
        os.remove(filepath)

    for filepath, sha1 in index.items():
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        _, content = read_object(sha1)
        with open(filepath, 'wb') as f:
            f.write(content)

    print(f"Switched to branch '{name}'")