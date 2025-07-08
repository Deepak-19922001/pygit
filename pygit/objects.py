import os
import zlib
import hashlib
import json
from .repository import find_pygit_dir


def read_object(sha1):
    pygit_dir = find_pygit_dir()
    if not pygit_dir: return None, None

    object_path = os.path.join(pygit_dir, 'objects', sha1)
    if not os.path.exists(object_path):
        return None, None

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

    tree_line = [line for line in content.decode().split('\n') if line.startswith('tree ')]
    if tree_line:
        return tree_line[0].split(' ')[1]
    return None


def get_tree_contents(tree_sha1):
    if not tree_sha1: return {}
    _, content = read_object(tree_sha1)
    if not content: return {}
    return json.loads(content.decode())


def pretty_print_object(sha1):
    obj_type, content = read_object(sha1)
    if not obj_type:
        print(f"fatal: bad object {sha1}")
        return

    if obj_type == 'commit':
        lines = content.decode().split('\n')
        metadata, message = [], []
        is_message = False
        for line in lines:
            if not line.strip() and not is_message:
                is_message = True
                continue
            if is_message:
                message.append(line)
            else:
                metadata.append(line)
        print(f"commit {sha1}")
        print('\n'.join(metadata))
        print('\n'.join(message))

    elif obj_type == 'tree':
        tree_data = get_tree_contents(sha1)
        for path, blob_sha in sorted(tree_data.items()):
            print(f"100644 blob {blob_sha}\t{path}")

    elif obj_type == 'blob':
        print(content.decode(errors='ignore'))

    elif obj_type == 'tag':
        lines = content.decode().split('\n')
        print(f"tag object {sha1}")
        for line in lines:
            print(line)

    else:
        print(f"fatal: unknown object type {obj_type}")
