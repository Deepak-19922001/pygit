import os
import zlib
import hashlib
import json
from .repository import find_pygit_dir

def read_object(sha1):
    pygit_dir = find_pygit_dir()
    if not pygit_dir: return None, None

    object_path = os.path.join(pygit_dir, 'objects', sha1)
    if not os.path.exists(object_path): return None, None

    with open(object_path, 'rb') as f:
        compressed_data = f.read()

    decompressed_data = zlib.decompress(compressed_data)
    header_end = decompressed_data.find(b'\0')
    header = decompressed_data[:header_end].decode()
    content = decompressed_data[header_end + 1:]

    obj_type, _ = header.split(' ')
    return obj_type, content

def hash_object(data, obj_type='blob'):
    pygit_dir = find_pygit_dir()
    if not pygit_dir: return None

    header = f'{obj_type} {len(data)}\0'.encode()
    full_data = header + data
    sha1 = hashlib.sha1(full_data).hexdigest()
    object_path = os.path.join(pygit_dir, 'objects', sha1)
    if not os.path.exists(object_path):
        with open(object_path, 'wb') as f:
            f.write(zlib.compress(full_data))
    return sha1

def get_commit_tree(commit_sha1):
    _, content = read_object(commit_sha1)
    if not content: return None

    tree_line = [line for line in content.decode().split('\n') if line.startswith('tree ') ]
    if tree_line:
        return tree_line[0].split(' ')[1]
    return None

def get_tree_contents(tree_sha1):
    if not tree_sha1: return {}
    _, content = read_object(tree_sha1)
    if not content: return {}
    return json.loads(content.decode())