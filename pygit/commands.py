import os
import sys
import collections
from datetime import datetime
import json
import fnmatch
import shutil

from .repository import find_pygit_dir, init as repo_init
from .objects import read_object, hash_object, get_commit_tree, get_tree_contents, pretty_print_object
from .index import read_index, write_index
from .refs import get_head_ref, get_head_commit, update_head, get_branch_commit, create_tag, list_tags, read_stash, \
    write_stash
from .diff import compare_files, compare_trees
from .utils import get_commit_history, find_common_ancestor, get_full_history_set
from .resolver import resolve_ref, resolve_ref_to_commit
from .config import read_config, write_config
from .remote import add_remote, remove_remote, list_remotes


def _read_gitignore():
    pygit_dir = find_pygit_dir()
    if not pygit_dir: return set()
    repo_root = os.path.dirname(pygit_dir)
    gitignore_path = os.path.join(repo_root, '.gitignore')
    if not os.path.exists(gitignore_path):
        return set()
    with open(gitignore_path, 'r') as f:
        return {line.strip() for line in f if line.strip() and not line.startswith('#')}


def _is_ignored(filepath, gitignore_patterns):
    filepath = filepath.replace(os.sep, '/')
    for pattern in gitignore_patterns:
        if pattern.endswith('/'):
            if filepath.startswith(pattern) or filepath == pattern.rstrip('/'):
                return True
        if fnmatch.fnmatch(filepath, pattern):
            return True
    return False


def _create_commit(message, tree_sha1, parents):
    config = read_config()
    author_name = config.get('user.name', 'PyGit User')
    author_email = config.get('user.email', 'user@pygit.com')
    author_string = f"{author_name} <{author_email}>"

    parent_lines = "".join(f"parent {p}\n" for p in parents) if parents else "parent None\n"

    commit_data = (
        f"tree {tree_sha1}\n"
        f"{parent_lines}"
        f"author {author_string} {datetime.now().isoformat()}\n"
        f"committer {author_string} {datetime.now().isoformat()}\n"
        f"\n"
        f"{message}\n"
    ).encode()
    return hash_object(commit_data, 'commit')


def _resolve_ref_or_head(ref_name, to_commit=True):
    if ref_name.upper() == 'HEAD':
        return get_head_commit()

    if to_commit:
        return resolve_ref_to_commit(ref_name)
    else:
        return resolve_ref(ref_name)


def init():
    repo_init()


def add(filepath):
    gitignore_patterns = _read_gitignore()
    if _is_ignored(filepath, gitignore_patterns):
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
        author_line = next((line for line in lines if line.startswith('author ')), "")
        print(f"Author: {author_line.split(' ', 1)[1]}")

        message_start_index = commit_content.find(b'\n\n') + 2
        print(f"\n    {commit_content[message_start_index:].decode().strip()}\n")


def status():
    head_ref = get_head_ref()
    head_commit = get_head_commit()

    if not head_ref.startswith('refs/heads/'):
        if head_commit:
            print(f"HEAD detached at {head_commit[:7]}")
        else:
            print("HEAD detached (no commit)")
    else:
        print(f"On branch {head_ref.split('/')[-1]}")

    head_tree = {}
    if head_commit:
        head_tree = get_tree_contents(get_commit_tree(head_commit))
    index_tree = read_index()

    staged_added, staged_deleted, staged_modified = compare_trees(head_tree, index_tree)
    print("\nChanges to be committed:")
    if not any([staged_added, staged_deleted, staged_modified]):
        print("  (no changes staged)")
    for f in sorted(staged_added): print(f"  new file:   {f}")
    for f in sorted(staged_modified): print(f"  modified:   {f}")
    for f in sorted(staged_deleted): print(f"  deleted:    {f}")
    print()

    unstaged_modified, unstaged_deleted, untracked_files = [], [], []
    pygit_dir = find_pygit_dir()
    repo_root = os.path.dirname(pygit_dir)
    gitignore_patterns = _read_gitignore()

    files_in_index = set(index_tree.keys())
    for root, dirs, files in os.walk(repo_root):
        if '.pygit' in dirs:
            dirs.remove('.pygit')

        for filename in files:
            filepath = os.path.relpath(os.path.join(root, filename), repo_root)
            if _is_ignored(filepath, gitignore_patterns):
                continue

            if filepath in files_in_index:
                with open(os.path.join(repo_root, filepath), 'rb') as f:
                    workdir_hash = hash_object(f.read(), 'blob')
                if workdir_hash != index_tree[filepath]:
                    unstaged_modified.append(filepath)
                files_in_index.remove(filepath)
            else:
                untracked_files.append(filepath)

    unstaged_deleted = list(files_in_index)

    print("Changes not staged for commit:")
    if not unstaged_modified and not unstaged_deleted:
        print("  (use 'pygit add <file>...' to stage changes)")
    for f in sorted(unstaged_modified): print(f"  modified:   {f}")
    for f in sorted(unstaged_deleted): print(f"  deleted:    {f}")
    print()

    print("Untracked files:")
    if not untracked_files:
        print("  (use 'pygit add <file>...' to include in what will be committed)")
    for f in sorted(untracked_files): print(f"  {f}")


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

    start_point_ref = start_point if start_point else 'HEAD'
    commit_hash = _resolve_ref_or_head(start_point_ref)
    if not commit_hash:
        print(f"Error: could not resolve '{start_point_ref}' to a commit.", file=sys.stderr)
        return False

    with open(new_branch_path, 'w') as f:
        f.write(commit_hash)
    print(f"Branch '{branch_name}' created.")


def checkout(name):
    pygit_dir = find_pygit_dir()
    repo_root = os.path.dirname(pygit_dir)

    old_head_commit = get_head_commit()
    old_tree = get_tree_contents(get_commit_tree(old_head_commit)) if old_head_commit else {}

    commit_sha1 = _resolve_ref_or_head(name)
    if not commit_sha1:
        print(f"Error: pathspec '{name}' did not match any file(s) known to pygit.", file=sys.stderr)
        return False

    new_tree = get_tree_contents(get_commit_tree(commit_sha1))

    files_to_delete = set(old_tree.keys()) - set(new_tree.keys())
    for filepath in files_to_delete:
        full_path = os.path.join(repo_root, filepath)
        if os.path.exists(full_path):
            os.remove(full_path)

    for filepath, sha1 in new_tree.items():
        full_path = os.path.join(repo_root, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
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

    write_index(new_tree)

    is_branch = get_branch_commit(name) is not None
    if is_branch:
        update_head(f'refs/heads/{name}', detached=False)
        print(f"Switched to branch '{name}'")
    else:
        update_head(commit_sha1, detached=True)
        print(f"Note: switching to '{name}'.")
        print("You are in 'detached HEAD' state.")


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

    if not other_commit or head_commit == other_commit:
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
        base_hash, head_hash, other_hash = base_tree.get(path), head_tree.get(path), other_tree.get(path)
        if base_hash == head_hash or head_hash == other_hash:
            if other_hash: merged_tree[path] = other_hash
        elif base_hash != other_hash:
            conflicts.append(path)

    if conflicts:
        print("Automatic merge failed; fix conflicts and then commit the result.")
        for path in conflicts:
            _, head_content = read_object(head_tree[path])
            _, other_content = read_object(other_tree[path])
            conflict_content = (
                f'<<<<<<< HEAD\n{head_content.decode()}\n=======\n{other_content.decode()}\n>>>>>>> {branch_name}\n').encode()
            with open(path, 'wb') as f: f.write(conflict_content)
            merged_tree[path] = hash_object(conflict_content, 'blob')
        write_index(merged_tree)
        return False

    print("Automatic merge successful.")

    commit_message = f"Merge branch '{branch_name}'"
    merged_tree_sha = hash_object(json.dumps(merged_tree, sort_keys=True).encode(), 'tree')
    merge_commit_sha = _create_commit(commit_message, merged_tree_sha, [head_commit, other_commit])

    head_ref = get_head_ref()
    pygit_dir = find_pygit_dir()
    branch_path = os.path.join(pygit_dir, head_ref)
    with open(branch_path, 'w') as f:
        f.write(merge_commit_sha)

    print(f"Merge made by the 'three-way' strategy. New commit: {merge_commit_sha[:7]}")
    checkout(get_head_ref().split('/')[-1])


def tag(*args):
    message = None
    if '-m' in args:
        m_index = args.index('-m')
        if m_index + 1 < len(args):
            message = args[m_index + 1]
            args = tuple(a for i, a in enumerate(args) if i not in [m_index, m_index + 1])

    if len(args) == 0:
        tags = list_tags()
        if not tags:
            print("No tags found.")
        for t in tags:
            print(t)
        return

    tag_name = args[0]
    commit_ref = args[1] if len(args) > 1 else 'HEAD'

    sha1 = _resolve_ref_or_head(commit_ref)
    if not sha1:
        print(f"Error: could not resolve '{commit_ref}' to a commit.")
        return False

    if create_tag(tag_name, sha1, message=message):
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
        stash_hash = _create_commit(message, index_tree_sha, [head_commit, workdir_tree_sha])

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
        workdir_tree_sha = [l.split(' ')[1] for l in lines if l.startswith('parent ')][1]

        index_tree = get_tree_contents(index_tree_sha)
        workdir_tree = get_tree_contents(workdir_tree_sha)

        write_index(index_tree)
        checkout(get_head_commit())

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
    gitignore_patterns = _read_gitignore()

    untracked_files, untracked_dirs = [], []

    for root, dirs, files in os.walk(repo_root):
        if '.pygit' in dirs:
            dirs.remove('.pygit')

        for name in files:
            filepath = os.path.relpath(os.path.join(root, name), repo_root)
            if filepath not in index_tree and not _is_ignored(filepath, gitignore_patterns):
                untracked_files.append(filepath)

        if clean_dirs:
            for name in dirs:
                dirpath = os.path.relpath(os.path.join(root, name), repo_root)
                if not any(f.startswith(dirpath) for f in index_tree) and not _is_ignored(dirpath, gitignore_patterns):
                    untracked_dirs.append(dirpath)

    if dry_run:
        for f in untracked_files: print(f"Would remove {f}")
        for d in untracked_dirs: print(f"Would remove {d}/")
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


def rebase(target_branch):
    current_ref = get_head_ref()
    if not current_ref.startswith('refs/heads/'):
        print("Cannot rebase: HEAD is detached.", file=sys.stderr)
        return False
    current_branch = current_ref.split('/')[-1]
    current_commit = get_head_commit()

    target_commit = get_branch_commit(target_branch)
    if not target_commit:
        print(f"Error: Branch '{target_branch}' does not exist.", file=sys.stderr)
        return False

    if current_commit == target_commit:
        print("Already up to date.")
        return True

    base_commit = find_common_ancestor(current_commit, target_commit)
    if not base_commit:
        print("Error: No common ancestor found.", file=sys.stderr)
        return False

    print(f"Rebasing {current_branch} onto {target_branch}")
    print(f"Common ancestor is {base_commit[:7]}")

    commits_to_replay = []
    target_history = get_full_history_set(target_commit)

    for commit_sha, content in get_commit_history(current_commit):
        if commit_sha in target_history or commit_sha == base_commit:
            break
        commits_to_replay.append((commit_sha, content))

    commits_to_replay.reverse()

    if not commits_to_replay:
        print("No commits to replay. Already up to date.")
        return True

    update_head(target_commit, detached=True)

    target_tree = get_tree_contents(get_commit_tree(target_commit))

    pygit_dir = find_pygit_dir()
    repo_root = os.path.dirname(pygit_dir)

    for filepath, sha1 in target_tree.items():
        full_path = os.path.join(repo_root, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        _, content = read_object(sha1)
        with open(full_path, 'wb') as f:
            f.write(content)

    new_base = target_commit
    for commit_sha, content in commits_to_replay:
        message_start = content.find(b'\n\n') + 2
        message = content[message_start:].decode().strip()

        original_tree = get_tree_contents(get_commit_tree(commit_sha))

        combined_tree = target_tree.copy()
        combined_tree.update(original_tree)

        combined_tree_sha = hash_object(json.dumps(combined_tree, sort_keys=True).encode(), 'tree')

        new_commit = _create_commit(message, combined_tree_sha, [new_base])

        new_base = new_commit

        target_tree = combined_tree

        print(f"Replayed commit: {commit_sha[:7]} -> {new_commit[:7]}")

    pygit_dir = find_pygit_dir()
    branch_path = os.path.join(pygit_dir, current_ref)
    with open(branch_path, 'w') as f:
        f.write(new_base)

    checkout(current_branch)

    print(f"Successfully rebased {current_branch} onto {target_branch}")
    return True


def show(ref_name='HEAD'):
    from .refs import get_tag_ref
    tag_sha1 = get_tag_ref(ref_name)

    if tag_sha1:
        obj_type, content = read_object(tag_sha1)
        if obj_type == 'tag':
            pretty_print_object(tag_sha1)
            commit_sha1 = content.decode().split('\n')[0].split(' ')[1]
            print("\n")
            pretty_print_object(commit_sha1)
            return True

    sha1 = _resolve_ref_or_head(ref_name, to_commit=True)
    if not sha1:
        print(f"fatal: ambiguous argument '{ref_name}': unknown revision or path not in the working tree.",
              file=sys.stderr)
        return False

    obj_type, content = read_object(sha1)
    pretty_print_object(sha1)

    if obj_type == 'tag':
        commit_sha1 = content.decode().split('\n')[0].split(' ')[1]
        print("\n")
        pretty_print_object(commit_sha1)


def remote(*args):
    if len(args) == 0:
        remotes = list_remotes()
        for name in remotes:
            print(name)
        return

    subcommand = args[0]
    if subcommand == 'add' and len(args) == 3:
        add_remote(args[1], args[2])
    elif subcommand == 'remove' and len(args) == 2:
        remove_remote(args[1])
    else:
        print("Usage: pygit remote [add <name> <url> | remove <name>]", file=sys.stderr)
        return False


def clone(url, directory=None):
    if not directory:
        directory = os.path.basename(url)
        if directory.endswith('.pygit'):
            directory = directory[:-6]

    if os.path.exists(directory):
        print(f"fatal: destination path '{directory}' already exists and is not an empty directory.")
        return False

    print(f"Cloning into '{directory}'...")
    os.makedirs(directory)
    os.chdir(directory)

    init()
    add_remote('origin', os.path.abspath(os.path.join('..', url)))

    # This is a placeholder for fetch, which we will implement next
    print("Cloning complete (fetch not yet implemented).")
