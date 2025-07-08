import os
from .config import read_config, write_config

def add_remote(name, url):
    config = read_config()
    if 'remote' not in config:
        config['remote'] = {}
    if name in config['remote']:
        print(f"fatal: remote {name} already exists.")
        return False
    config['remote'][name] = {'url': url}
    write_config(config)
    return True

def remove_remote(name):
    config = read_config()
    if 'remote' not in config or name not in config['remote']:
        print(f"fatal: no such remote: {name}")
        return False
    del config['remote'][name]
    write_config(config)
    return True

def list_remotes():
    config = read_config()
    return config.get('remote', {})
