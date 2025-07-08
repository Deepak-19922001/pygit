import os
import sys
import collections
from datetime import datetime
import json
import fnmatch
import shutil

from .repository import find_pygit_dir, init as repo_init
from .objects import read_object, hash_object, get_commit_tree, get_tree_contents
from .index import read_index, write_index
from .refs import get_head_ref, get_head_commit, update_head, get_branch_commit, create_tag, list_tags, read_stash, \
    write_stash
from .diff import compare_files, compare_trees
from .utils import get_commit_history, find_common_ancestor, get_full_history_set
from .resolver import resolve_ref
from .config import read_config, write_config


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
        return False

    with open(filepath, 'rb') as f:
        content = f.read()
    sha1 = hash_object(content, 'blob')
    if not sha1: return False

    index = read_index()
    index[filepath] = sha1
    write_index(index)

    print(f"Staged '{filepath}' for commit.")


def rm(filepath):
    index = read_index()

    if filepath not in index:
        print(f"fatal: pathspec '{filepath}' did not match any files", file=sys.stderr)
        return False

    del index[filepath]
    write_index(index)

    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass
    except OSError as e:
        print(f"Error removing file {filepath}: {e}", file=sys.stderr)
        return False

    print(f"rm '{filepath}'")


def _create_commit(message, tree_sha1, parents):
    """Internal helper to create a commit object."""
    config = read_config()
    author_name = config.get('user.name', 'PyGit User')
    author_email = config.get('user.email', 'user@pygit.com')
    author_string = f"{author_name} <{author_email}>"

    parent_lines = "".join(f"parent {p}\n" for p in parents)

    commit_data = (
        f"tree {tree_sha1}\n"
        f"{parent_lines}"
        f"author {author_string} {datetime.now().isoformat()}\n"
        f"committer {author_string} {datetime.now().isoformat()}\n"
        f"\n"
        f"{message}\n"
    ).encode()
    return hash_object(commit_data, 'commit')


def commit(*args):
    if not args or args[0] != '-m' or len(args) < 2:
        print("Usage: pygit commit -m <message>", file=sys.stderr)
        return False
    message = args[1]

    index = read_index()
    if not index:
        print("Nothing to commit, staging area is empty.")
        return

    tree_sha1 = hash_object(json.dumps(index, sort_keys=True).encode(), 'tree')
    parent_sha1 = get_head_commit()
    parents = [parent_sha1] if parent_sha1 else []

    commit_sha1 = _create_commit(message, tree_sha1, parents)

    head_ref = get_head_ref()
    if head_ref.startswith('refs/heads/'):
        pygit_dir = find_pygit_dir()
        branch_path = os.path.join(pygit_dir, head_ref)
        with open(branch_path, 'w') as f:
            f.write(commit_sha1)
    else:
        update_head(commit_sha1, detached=True)

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

    head_commit = get_head_commit()
    head_tree_sha = get_commit_tree(head_commit)
    head_tree = get_tree_contents(head_tree_sha)
    index_tree = read_index()

    pygit_dir = find_pygit_dir()
    repo_root = os.path.dirname(pygit_dir)
    gitignore_patterns = read_gitignore()

    workdir_tree = {}
    for root, dirs, files in os.walk(repo_root):
        if '.pygit' in dirs:
            dirs.remove('.pygit')

        for filename in files:
            filepath = os.path.relpath(os.path.join(root, filename), repo_root)
            if not is_ignored(filepath, gitignore_patterns):
                with open(os.path.join(repo_root, filepath), 'rb') as f:
                    workdir_tree[filepath] = hash_object(f.read(), 'blob')

    all_files = set(head_tree.keys()) | set(index_tree.keys()) | set(workdir_tree.keys())

    staged_modified, staged_added, staged_deleted = [], [], []
    unstaged_modified, unstaged_deleted = [], []
    untracked_files = []

    for path in sorted(list(all_files)):
        head_hash = head_tree.get(path)
        index_hash = index_tree.get(path)
        workdir_hash = workdir_tree.get(path)

        if head_hash != index_hash:
            if head_hash is None:
                staged_added.append(path)
            elif index_hash is None:
                staged_deleted.append(path)
            else:
                staged_modified.append(path)

        if index_hash != workdir_hash:
            if index_hash is None:
                untracked_files.append(path)
            elif workdir_hash is None:
                unstaged_deleted.append(path)
            else:
                unstaged_modified.append(path)

    print("\nChanges to be committed:")
    if not any([staged_added, staged_deleted, staged_modified]):
        print("  (no changes staged)")
    for f in staged_added: print(f"  new file:   {f}")
    for f in staged_modified: print(f"  modified:   {f}")
    for f in staged_deleted: print(f"  deleted:    {f}")
    print()

    print("Changes not staged for commit:")
    if not unstaged_modified and not unstaged_deleted:
        print("  (use 'pygit add <file>...' to stage changes)")
    for f in unstaged_modified: print(f"  modified:   {f}")
    for f in unstaged_deleted: print(f"  deleted:    {f}")
    print()

    print("Untracked files:")
    if not untracked_files:
        print("  (use 'pygit add <file>...' to include in what will be committed)")
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
        return False

    if start_point:
        commit_hash = resolve_ref(start_point)
        if not commit_hash:
            print(f"Error: could not resolve '{start_point}' to a commit.", file=sys.stderr)
            return False
    else:
        commit_hash = get_head_commit()

    if not commit_hash:
        print("Error: Cannot create branch from an empty repository or invalid start point.", file=sys.stderr)
        return False

    with open(new_branch_path, 'w') as f:
        f.write(commit_hash)
    print(f"Branch '{branch_name}' created.")


def checkout(name):
    pygit_dir = find_pygit_dir()
    repo_root = os.path.dirname(pygit_dir)

    old_head_commit = get_head_commit()
    old_head_tree = get_tree_contents(get_commit_tree(old_head_commit))

    commit_sha1 = resolve_ref(name)
    if not commit_sha1:
        print(f"Error: pathspec '{name}' did not match any file(s) known to pygit.", file=sys.stderr)
        return False

    new_tree = get_tree_contents(get_commit_tree(commit_sha1))

    is_branch = get_branch_commit(name) is not None
    if is_branch:
        update_head(f'refs/heads/{name}', detached=False)
        print(f"Switched to branch '{name}'")
    else:
        update_head(commit_sha1, detached=True)
        print(f"Note: switching to '{name}'.")
        print("You are in 'detached HEAD' state.")
    write_index(new_tree)

    files_to_delete = set(old_head_tree.keys()) - set(new_tree.keys())
    for filepath in files_to_delete:
        full_path = os.path.join(repo_root, filepath)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass

    for filepath, sha1 in new_tree.items():
        full_path = os.path.join(repo_root, filepath)
        dir_name = os.path.dirname(full_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        _, content = read_object(sha1)
        with open(full_path, 'wb') as f:
            f.write(content)

    for filepath in files_to_delete:
        dir_name = os.path.dirname(os.path.join(repo_root, filepath))
        try:
            if dir_name and not os.listdir(dir_name):
                os.rmdir(dir_name)
        except OSError:
            pass


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
    other_commit = get_branch_commit(branch_name)

    if not other_commit:
        print(f"Error: branch '{branch_name}' not found.", file=sys.stderr)
        return False

    if head_commit == other_commit:
        print("Already up to date.")
        return

    head_history = get_full_history_set(head_commit)
    if other_commit in head_history:
        print("Already up to date.")
        return

    other_history = get_full_history_set(other_commit)
    if head_commit in other_history:
        print(f"Fast-forwarding to {branch_name}")
        checkout(branch_name)
        return

    base_commit = find_common_ancestor(head_commit, other_commit)
    if not base_commit:
        print("Error: No common ancestor found.", file=sys.stderr)
        return False

    print(f"Merging {branch_name} into {get_head_ref().split('/')[-1]}")
    print(f"Common ancestor is {base_commit[:7]}")

    base_tree = get_tree_contents(get_commit_tree(base_commit))
    head_tree = get_tree_contents(get_commit_tree(head_commit))
    other_tree = get_tree_contents(get_commit_tree(other_commit))

    all_files = set(base_tree.keys()) | set(head_tree.keys()) | set(other_tree.keys())

    merged_tree = head_tree.copy()
    conflicts = []

    for path in sorted(list(all_files)):
        base_hash = base_tree.get(path)
        head_hash = head_tree.get(path)
        other_hash = other_tree.get(path)

        if base_hash == head_hash:
            if other_hash:
                merged_tree[path] = other_hash
        elif base_hash == other_hash:
            pass
        elif head_hash != other_hash:
            conflicts.append(path)
        else:
            pass

    if conflicts:
        print("Automatic merge failed; fix conflicts and then commit the result.")
        for path in conflicts:
            _, head_content = read_object(head_tree[path])
            _, other_content = read_object(other_tree[path])

            conflict_content = (
                    b'<<<<<<< HEAD\n' +
                    head_content +
                    b'=======\n' +
                    other_content +
                    b'>>>>>>> ' + branch_name.encode() + b'\n'
            )
            with open(path, 'wb') as f:
                f.write(conflict_content)
            merged_tree[path] = hash_object(conflict_content, 'blob')
        write_index(merged_tree)
        return False

    print("Automatic merge successful.")

    commit_message = f"Merge branch '{branch_name}'"
    merged_tree_sha = hash_object(json.dumps(merged_tree, sort_keys=True).encode(), 'tree')
    merge_commit_sha = _create_commit(
        commit_message,
        merged_tree_sha,
        [head_commit, other_commit]
    )

    head_ref = get_head_ref()
    pygit_dir = find_pygit_dir()
    branch_path = os.path.join(pygit_dir, head_ref)
    with open(branch_path, 'w') as f:
        f.write(merge_commit_sha)

    print(f"Merge made by the 'three-way' strategy. New commit: {merge_commit_sha[:7]}")

    # Update working directory and index
    write_index(merged_tree)
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
        return False

    if create_tag(tag_name, sha1):
        print(f"Tag '{tag_name}' created for commit {sha1[:7]}")


def stash(*args):
    if not args or args[0] not in ['push', 'list', 'pop', 'apply']:
        print("Usage: pygit stash [push|list|pop|apply]", file=sys.stderr)
        return False

    subcommand = args[0]

    if subcommand == 'list':
        stashes = read_stash()
        if not stashes:
            print("No stashes to list.")
            return
        for i, stash_hash in enumerate(stashes):
            print(f"stash@{{{i}}}: {stash_hash}")
        return

    if subcommand == 'push':
        head_commit = get_head_commit()
        index_tree = read_index()

        pygit_dir = find_pygit_dir()
        repo_root = os.path.dirname(pygit_dir)
        workdir_tree = {}
        for filepath in index_tree.keys():
            full_path = os.path.join(repo_root, filepath)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    workdir_tree[filepath] = hash_object(f.read(), 'blob')

        index_tree_sha = hash_object(json.dumps(index_tree, sort_keys=True).encode(), 'tree')
        workdir_tree_sha = hash_object(json.dumps(workdir_tree, sort_keys=True).encode(), 'tree')

        if index_tree_sha == get_commit_tree(head_commit) and workdir_tree == index_tree:
            print("No local changes to save")
            return

        message = f"Stash on {get_head_ref()}: WIP"
        stash_commit_data = (
            f"tree {index_tree_sha}\n"
            f"parent {head_commit}\n"
            f"parent {workdir_tree_sha}\n"
            f"author PyGit Stash <stash@pygit.com> {datetime.now().isoformat()}\n"
            f"\n"
            f"{message}\n"
        ).encode()

        stash_hash = hash_object(stash_commit_data, 'commit')

        stashes = read_stash()
        stashes.insert(0, stash_hash)
        write_stash(stashes)

        checkout(head_commit)
        write_index(get_tree_contents(get_commit_tree(head_commit)))

        print(f"Saved working directory and index state as stash@{{{len(stashes) - 1}}}")
        return

    if subcommand in ['pop', 'apply']:
        stashes = read_stash()
        if not stashes:
            print("No stashes to apply.")
            return False

        stash_hash = stashes[0]
        _, stash_content = read_object(stash_hash)
        lines = stash_content.decode().split('\n')

        index_tree_sha = lines[0].split(' ')[1]
        workdir_tree_sha = lines[2].split(' ')[1]

        index_tree = get_tree_contents(index_tree_sha)
        workdir_tree = get_tree_contents(workdir_tree_sha)

        write_index(index_tree)
        for filepath, sha1 in workdir_tree.items():
            _, content = read_object(sha1)
            with open(filepath, 'wb') as f:
                f.write(content)

        print(f"Applied stash@{{0}}")

        if subcommand == 'pop':
            write_stash(stashes[1:])
            print("Dropped refs/stash@{0}")
        return


def clean(*args):
    dry_run = '-n' in args or '--dry-run' in args
    force = '-f' in args or '--force' in args
    clean_dirs = '-d' in args

    if not force and not dry_run:
        print("fatal: clean.requireForce is true and neither -i, -n, nor -f given; "
              "refusing to clean")
        return False

    index_tree = read_index()
    pygit_dir = find_pygit_dir()
    repo_root = os.path.dirname(pygit_dir)
    gitignore_patterns = read_gitignore()

    untracked_files = []
    untracked_dirs = []

    for root, dirs, files in os.walk(repo_root):
        if '.pygit' in dirs:
            dirs.remove('.pygit')

        for name in files:
            filepath = os.path.relpath(os.path.join(root, name), repo_root)
            if filepath not in index_tree and not is_ignored(filepath, gitignore_patterns):
                untracked_files.append(filepath)

        if clean_dirs:
            for name in dirs:
                dirpath = os.path.relpath(os.path.join(root, name), repo_root)
                if not any(f.startswith(dirpath) for f in index_tree) and not is_ignored(dirpath, gitignore_patterns):
                    is_empty_of_tracked = True
                    for _, _, inner_files in os.walk(dirpath):
                        if any(os.path.relpath(os.path.join(dirpath, f), repo_root) in index_tree for f in inner_files):
                            is_empty_of_tracked = False
                            break
                    if is_empty_of_tracked:
                        untracked_dirs.append(dirpath)

    if dry_run:
        for f in untracked_files:
            print(f"Would remove {f}")
        for d in untracked_dirs:
            print(f"Would remove {d}/")
        return

    for f in untracked_files:
        print(f"Removing {f}")
        os.remove(os.path.join(repo_root, f))

    for d in sorted(untracked_dirs, reverse=True):
        print(f"Removing {d}/")
        try:
            shutil.rmtree(os.path.join(repo_root, d))
        except OSError as e:
            print(f"Error removing directory {d}: {e}", file=sys.stderr)


def config(*args):
    if len(args) == 0:
        print("Usage: pygit config <key> [<value>]", file=sys.stderr)
        return False

    key = args[0]
    config_data = read_config()

    if len(args) == 1:
        value = config_data.get(key)
        if value:
            print(value)
        else:
            return False
    elif len(args) == 2:
        value = args[1]
        config_data[key] = value
        write_config(config_data)
    else:
        print("Usage: pygit config <key> [<value>]", file=sys.stderr)
        return False
