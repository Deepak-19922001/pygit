import os
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

    ref_path = os.path.join(pygit_dir, head_ref_path)
    if not os.path.exists(ref_path):
        if os.path.basename(head_ref_path) == head_ref_path:
            return head_ref_path
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


def update_head(ref_path):
    pygit_dir = find_pygit_dir()
    head_file = os.path.join(pygit_dir, 'HEAD')
    with open(head_file, 'w') as f:
        f.write(f'ref: {ref_path}')