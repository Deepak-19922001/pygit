import os
import json
from .repository import find_pygit_dir

def get_config_path():
    pygit_dir = find_pygit_dir()
    if not pygit_dir:
        return None
    return os.path.join(pygit_dir, 'config')


def read_config():
    config_path = get_config_path()
    if not config_path or not os.path.exists(config_path):
        return {}

    with open(config_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def write_config(config_data):
    config_path = get_config_path()
    if not config_path:
        return
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=4)
