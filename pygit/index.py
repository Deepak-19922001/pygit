import os
import json
from .repository import find_pygit_dir

def read_index():
    pygit_dir = find_pygit_dir()
    index_path = os.path.join(pygit_dir, 'index')
    try:
        with open(index_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_index(index_data):
    pygit_dir = find_pygit_dir()
    index_path = os.path.join(pygit_dir, 'index')
    with open(index_path, 'w') as f:
        json.dump(index_data, f, indent = 4)