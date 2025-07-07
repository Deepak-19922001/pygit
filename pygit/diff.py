import difflib
from .objects import read_object


def compare_files(from_sha1, to_sha1, from_path, to_path):
    _, from_content = read_object(from_sha1)
    _, to_content = read_object(to_sha1)

    # It's better to treat content as lines for difflib
    from_lines = from_content.decode(errors='ignore').splitlines()
    to_lines = to_content.decode(errors='ignore').splitlines()

    diff = difflib.unified_diff(
        from_lines,
        to_lines,
        fromfile=f"a/{from_path}",
        tofile=f"b/{to_path}",
        lineterm=''
    )

    return list(diff)


def compare_trees(from_tree, to_tree):
    from_files = set(from_tree.keys())
    to_files = set(to_tree.keys())

    added = to_files - from_files
    deleted = from_files - to_files

    potential_modified = from_files & to_files
    modified = {
        f for f in potential_modified if from_tree[f] != to_tree[f]
    }

    return added, deleted, modified
