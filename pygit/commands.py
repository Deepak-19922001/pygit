import os
import sys
import collections
from datetime import datetime
import json
import fnmatch

from .repository import find_pygit_dir, init as repo_init
from .objects import read_object, hash_object, get_commit_tree, get_tree_contents
from .index import read_index, write_index
from .refs import get_head_ref, get_head_commit, update_head, get_branch_commit, create_tag, list_tags
from .diff import compare_files, compare_trees
from .utils import get_commit_history
from .resolver import resolve_ref


def read_gitignore():
    pygit_dir = find_pygit_dir()
    if not pygit_dir: return set()
    repo_root = os.path.dirname(pygit_dir)
    gitignore_path = os.path.join(repo_root, '.gitignore')
    if not os.path.exists(gitignore_path):
        return set()
    with open(gitignore_path, 'r') as f:
        return {line.strip() for line in f if line.strip() and not line.startswith('#')}


def is_ignored(filepath, gitignore_patterns):
    filepath = filepath.replace(os.sep, '/')
    for pattern in gitignore_patterns:
        if pattern.endswith('/'):
            if filepath.startswith(pattern) or filepath == pattern.rstrip('/'):
                return True
        if fnmatch.fnmatch(filepath, pattern):
            return True
    return False


def init():
    repo_init()


def add(filepath):
    gitignore_patterns = read_gitignore()
    if is_ignored(filepath, gitignore_patterns):
        print(f"Ignoring '{filepath}' due to .gitignore")
        return

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

    head_ref_path = get_head_ref()
    if head_ref_path.startswith('refs/heads/'):
        pygit_dir = find_pygit_dir()
        ref_full_path = os.path.join(pygit_dir, head_ref_path)
        os.makedirs(os.path.dirname(ref_full_path), exist_ok=True)
        with open(ref_full_path, 'w') as f:
            f.write(commit_sha1)

    update_head(commit_sha1, detached=not head_ref_path.startswith('refs/heads/'))

    write_index({})
    print(f"Committed, commit hash: {commit_sha1}")


def log():
    for commit_sha1, commit_content in get_commit_history(get_head_commit()):
        print(f"commit {commit_sha1}")

        lines = commit_content.decode().split('\n')
        author_line = next(line for line in lines if line.startswith('author '))
        print(f"Author: {author_line.split(' ', 1)[1]}")

        message_start_index = commit_content.find(b'\n\n') + 2
        print(f"\n    {commit_content[message_start_index:].decode().strip()}\n")


def status():
    head_ref = get_head_ref()
    if not head_ref.startswith('refs/heads/'):
        print(f"HEAD detached at {get_head_commit()[:7]}")
    else:
        print(f"On branch {head_ref.split('/')[-1]}")

    gitignore_patterns = read_gitignore()
    head_commit = get_head_commit()
    head_tree_sha = get_commit_tree(head_commit)
    head_tree = get_tree_contents(head_tree_sha)
    index = read_index()

    added, deleted, modified = compare_trees(head_tree, index)
    print("\nChanges to be committed:")
    if not any([added, deleted, modified]): print("  (no changes staged)")
    for f in added: print(f"  new file:   {f}")
    for f in modified: print(f"  modified:   {f}")
    for f in deleted: print(f"  deleted:    {f}")
    print()

    unstaged_changes = collections.defaultdict(list)
    untracked_files = []

    pygit_dir = find_pygit_dir()
    repo_root = os.path.dirname(pygit_dir)
    all_tracked_files = set(index.keys()) | set(head_tree.keys())

    for root, dirs, files in os.walk(repo_root):
        if '.pygit' in dirs:
            dirs.remove('.pygit')

        for filename in files:
            filepath = os.path.relpath(os.path.join(root, filename), repo_root)
            if is_ignored(filepath, gitignore_patterns):
                continue

            if filepath not in all_tracked_files:
                untracked_files.append(filepath)
                continue

            if filepath not in index:
                unstaged_changes['deleted'].append(filepath)
                continue

            with open(os.path.join(repo_root, filepath), 'rb') as f:
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


def branch(branch_name=None, start_point=None):
    pygit_dir = find_pygit_dir()
    heads_dir = os.path.join(pygit_dir, 'refs', 'heads')
    head_ref = get_head_ref()
    current_branch = head_ref.split('/')[-1] if head_ref.startswith('refs/heads/') else None

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

    if start_point:
        commit_hash = resolve_ref(start_point)
        if not commit_hash:
            print(f"Error: could not resolve '{start_point}' to a commit.", file=sys.stderr)
            return
    else:
        commit_hash = get_head_commit()

    if not commit_hash:
        print("Error: Cannot create branch from an empty repository or invalid start point.", file=sys.stderr)
        return

    with open(new_branch_path, 'w') as f:
        f.write(commit_hash)
    print(f"Branch '{branch_name}' created.")


def checkout(name):
    commit_sha1 = resolve_ref(name)

    if not commit_sha1:
        print(f"Error: pathspec '{name}' did not match any file(s) known to pygit.", file=sys.stderr)
        return

    is_branch = get_branch_commit(name) is not None

    if is_branch:
        update_head(f'refs/heads/{name}', detached=False)
        print(f"Switched to branch '{name}'")
    else:
        update_head(commit_sha1, detached=True)
        print(f"Note: switching to '{name}'.")
        print("You are in 'detached HEAD' state.")

    tree_sha1 = get_commit_tree(commit_sha1)
    tree_contents = get_tree_contents(tree_sha1)
    write_index(tree_contents)

    pygit_dir = find_pygit_dir()
    repo_root = os.path.dirname(pygit_dir)
    index = read_index()
    workdir_files = set()
    for root, dirs, files in os.walk(repo_root):
        if '.pygit' in dirs:
            dirs.remove('.pygit')
        for filename in files:
            filepath = os.path.relpath(os.path.join(root, filename), repo_root)
            workdir_files.add(filepath)

    for filepath in workdir_files - set(index.keys()):
        os.remove(os.path.join(repo_root, filepath))

    for filepath, sha1 in index.items():
        full_path = os.path.join(repo_root, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        _, content = read_object(sha1)
        with open(full_path, 'wb') as f:
            f.write(content)


def diff(staged=None):
    if staged == '--staged':
        head_commit = get_head_commit()
        head_tree_sha = get_commit_tree(head_commit)
        from_tree = get_tree_contents(head_tree_sha)
        to_tree = read_index()
    else:
        from_tree = read_index()
        to_tree = {}
        for filepath in from_tree:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    to_tree[filepath] = hash_object(f.read())

    added, deleted, modified = compare_trees(from_tree, to_tree)

    for f in added: print(f"Added: {f}")
    for f in deleted: print(f"Deleted: {f}")
    for f in modified:
        diff_output = compare_files(from_tree[f], to_tree[f], f, f)
        for line in diff_output:
            print(line)


def merge(branch_name):
    head_commit = get_head_commit()
    target_commit = get_branch_commit(branch_name)

    if not target_commit:
        print(f"Error: branch '{branch_name}' does not exist or has no commits.", file=sys.stderr)
        return

    history = {sha for sha, _ in get_commit_history(target_commit)}
    if head_commit not in history:
        print("Non-fast-forward merge is not supported.", file=sys.stderr)
        return

    current_branch_ref = get_head_ref()
    pygit_dir = find_pygit_dir()
    ref_full_path = os.path.join(pygit_dir, current_branch_ref)

    with open(ref_full_path, 'w') as f:
        f.write(target_commit)

    print(f"Merged {branch_name} (fast-forward).")
    checkout(get_head_ref().split('/')[-1])


def tag(tag_name=None, commit_ref=None):
    if not tag_name:
        tags = list_tags()
        if not tags:
            print("No tags found.")
        for t in tags:
            print(t)
        return

    commit_to_tag = commit_ref if commit_ref else get_head_commit()
    sha1 = resolve_ref(commit_to_tag)
    if not sha1:
        print(f"Error: could not resolve '{commit_to_tag}' to a commit.")
        return

    if create_tag(tag_name, sha1):
        print(f"Tag '{tag_name}' created for commit {sha1[:7]}")
