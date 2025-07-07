import os
import sys
from .repository import find_pygit_dir


def get_head_ref():
    pygit_dir = find_pygit_dir()
    head_path = os.path.join(pygit_dir, 'HEAD')
    with open(head_path, 'r') as f:
        content = f.read().strip()
    if content.startswith('ref:'):
        return content.split(' ')[1]
    return content


def get_head_commit():
    pygit_dir = find_pygit_dir()
    head_ref_path = get_head_ref()

    if len(head_ref_path) == 40 and all(c in '0123456789abcdef' for c in head_ref_path):
        return head_ref_path

    ref_path = os.path.join(pygit_dir, head_ref_path)
    if not os.path.exists(ref_path):
        return None

    with open(ref_path, 'r') as f:
        return f.read().strip()


def get_branch_commit(branch_name):
    pygit_dir = find_pygit_dir()
    branch_path = os.path.join(pygit_dir, 'refs', 'heads', branch_name)
    if not os.path.exists(branch_path):
        return None
    with open(branch_path, 'r') as f:
        return f.read().strip()


def update_head(ref, detached=False):
    pygit_dir = find_pygit_dir()
    head_file = os.path.join(pygit_dir, 'HEAD')
    with open(head_file, 'w') as f:
        if detached:
            f.write(ref)
        else:
            f.write(f'ref: {ref}')

def create_tag(tag_name, commit_sha1):
    pygit_dir = find_pygit_dir()
    tags_dir = os.path.join(pygit_dir, 'refs', 'tags')
    os.makedirs(tags_dir, exist_ok=True)

    tag_path = os.path.join(tags_dir, tag_name)
    if os.path.exists(tag_path):
        print(f"Error: tag '{tag_name}' already exists.", file=sys.stderr)
        return False

    with open(tag_path, 'w') as f:
        f.write(commit_sha1)
    return True


def list_tags():
    pygit_dir = find_pygit_dir()
    tags_dir = os.path.join(pygit_dir, 'refs', 'tags')
    if not os.path.exists(tags_dir):
        return []
    return sorted(os.listdir(tags_dir))


def get_tag_commit(tag_name):
    pygit_dir = find_pygit_dir()
    tag_path = os.path.join(pygit_dir, 'refs', 'tags', tag_name)
    if not os.path.exists(tag_path):
        return None
    with open(tag_path, 'r') as f:
        return f.read().strip()
