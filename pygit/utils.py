import collections
from .objects import read_object


def get_commit_parents(commit_content):
    parents = []
    for line in commit_content.decode().split('\n'):
        if line.startswith('parent '):
            parent_sha = line.split(' ')[1]
            if parent_sha != 'None':
                parents.append(parent_sha)
    return parents


def get_commit_history(start_commit_sha1):
    commit_sha1 = start_commit_sha1
    while commit_sha1:
        obj_type, content = read_object(commit_sha1)
        if obj_type != 'commit':
            return

        yield commit_sha1, content

        parents = get_commit_parents(content)
        commit_sha1 = parents[0] if parents else None


def get_full_history_set(start_commit_sha1):
    if not start_commit_sha1:
        return set()
    history = set()
    q = collections.deque([start_commit_sha1])
    visited = {start_commit_sha1}

    while q:
        commit_sha1 = q.popleft()
        if not commit_sha1:
            continue

        history.add(commit_sha1)

        _, content = read_object(commit_sha1)
        if not content: continue

        parents = get_commit_parents(content)
        for parent in parents:
            if parent not in visited:
                visited.add(parent)
                q.append(parent)
    return history


def find_common_ancestor(commit1_sha, commit2_sha):
    history1 = get_full_history_set(commit1_sha)

    q = collections.deque([commit2_sha])
    visited = {commit2_sha}

    while q:
        current_sha = q.popleft()
        if current_sha in history1:
            return current_sha

        _, content = read_object(current_sha)
        if not content: continue

        parents = get_commit_parents(content)
        for parent in parents:
            if parent not in visited:
                visited.add(parent)
                q.append(parent)
    return None
