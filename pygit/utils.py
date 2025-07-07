from .objects import read_object
def get_commit_history(start_commit_sha1):
    commit_sha1 = start_commit_sha1
    while commit_sha1:
        obj_type, content = read_object(commit_sha1)
        if obj_type != 'commit':
            return
        yield commit_sha1, content
        commit_content_str = content.decode()
        lines = commit_content_str.split('\n')
        parent_line = next((line for line in lines if line.startswith('parent ')), None)

        if parent_line and parent_line.split(' ')[1] != 'None':
            commit_sha1 = parent_line.split(' ')[1]
        else:
            commit_sha1 = None