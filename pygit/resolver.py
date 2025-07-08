import os
from .repository import find_pygit_dir
from .refs import get_branch_commit, get_tag_ref
from .objects import read_object


def resolve_ref_to_commit(ref_name):
    if not ref_name:
        return None

    sha1 = resolve_ref(ref_name)
    if not sha1:
        return None
    while True:
        obj_type, content = read_object(sha1)
        if obj_type == 'commit':
            return sha1
        elif obj_type == 'tag':
            sha1 = content.decode().split('\n')[0].split(' ')[1]
        else:
            return None


def resolve_ref(name):
    pygit_dir = find_pygit_dir()
    if not pygit_dir:
        return None

    commit = get_branch_commit(name)
    if commit:
        return commit

    tag_ref = get_tag_ref(name)
    if tag_ref:
        return tag_ref

    if len(name) >= 4 and all(c in '0123456789abcdef' for c in name.lower()):
        name = name.lower()
        objects_dir = os.path.join(pygit_dir, 'objects')

        matches = [obj for obj in os.listdir(objects_dir) if obj.startswith(name)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(f"Error: ref '{name}' is ambiguous.")
            return None

    return None
