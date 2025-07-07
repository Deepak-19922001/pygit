import os
from .repository import find_pygit_dir
from .refs import get_branch_commit, get_tag_commit
from .objects import read_object


def resolve_ref(name):
    pygit_dir = find_pygit_dir()
    if not pygit_dir:
        return None

    commit = get_branch_commit(name)
    if commit:
        return commit

    commit = get_tag_commit(name)
    if commit:
        return commit
    if len(name) >= 4 and all(c in '0123456789abcdef' for c in name.lower()):
        name = name.lower()
        objects_dir = os.path.join(pygit_dir, 'objects')
        matches = [obj for obj in os.listdir(objects_dir) if obj.startswith(name)]

        commit_matches = []
        for match in matches:
            obj_type, _ = read_object(match)
            if obj_type == 'commit':
                commit_matches.append(match)

        if len(commit_matches) == 1:
            return commit_matches[0]
        elif len(commit_matches) > 1:
            print(f"Error: ref '{name}' is ambiguous.")
            return None

    return None
