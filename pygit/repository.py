import os
import json
PYGIT_DIR = '.pygit'

def find_pygit_dir():
    current_dir = os.getcwd()
    while current_dir != os.path.dirname(current_dir):
        pygit_dir = os.path.join(current_dir, PYGIT_DIR)
        if os.path.isdir(pygit_dir):
            return pygit_dir
    return None

def init():
    if os.path.exists(PYGIT_DIR):
        print(f"Error: PyGit repository already initialized in {os.path.abspath(PYGIT_DIR)}")
        return
    os.makedirs(os.path.join(PYGIT_DIR, 'objects'))
    os.makedirs(os.path.join(PYGIT_DIR, 'refs', 'heads'))

    with open(os.path.join(PYGIT_DIR, 'HEAD'), 'w') as f:
        f.write('ref: refs/heads/main\n')
    with open(os.path.join(PYGIT_DIR, 'index'), 'w') as f:
        json.dump({}, f)

    print(f"PyGit repository initialized in {os.path.abspath(PYGIT_DIR)}")
