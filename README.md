# PyGit

PyGit is a lightweight, Python-based implementation of Git, designed to provide core version control functionality. It's a great tool for learning how Git works under the hood or for use in environments where a full Git installation is not available.

## Features

PyGit implements many of the core Git features:

- **Repository Management**: Initialize repositories with `init`
- **Version Control**: Track changes with `add`, `commit`, and view history with `log`
- **Branching and Merging**: Create and switch branches with `branch` and `checkout`, merge with `merge`
- **Rebasing**: Rewrite commit history with `rebase` for a cleaner, linear history
- **Tagging**: Mark specific points in history with `tag`
- **Stashing**: Temporarily store changes with `stash`
- **Configuration**: Set repository-specific settings with `config`
- **Status and Diff**: Check repository status with `status` and view changes with `diff`
- **Cleaning**: Remove untracked files with `clean`
- **.gitignore Support**: Ignore files based on patterns in `.gitignore`
- **Detached HEAD**: Work with commits directly without a branch
- **Annotated Tags**: Create tags with messages

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/deepak-19922001/pygit.git
   cd pygit
   ```

2. Make the main script executable (optional):
   ```bash
   chmod +x pygit.py
   ```

3. You can run PyGit directly:
   ```bash
   ./pygit.py <command> [<args>]
   ```

   Or using Python:
   ```bash
   python3 pygit.py <command> [<args>]
   ```

## Usage

Here are some examples of how to use PyGit:

### Initialize a Repository
```bash
python3 pygit.py init
```

### Add Files to Staging
```bash
python3 pygit.py add file.txt
```

### Commit Changes
```bash
python3 pygit.py commit -m "Initial commit"
```

### View Commit History
```bash
python3 pygit.py log
```

### Create and Switch Branches
```bash
python3 pygit.py branch feature-branch
python3 pygit.py checkout feature-branch
```

### Create a Tag
```bash
python3 pygit.py tag v1.0
```

### Create an Annotated Tag
```bash
python3 pygit.py tag -m "Version 1.0 release" v1.0
```

### Stash Changes
```bash
python3 pygit.py stash push
python3 pygit.py stash list
python3 pygit.py stash pop
```

### Merge Branches
```bash
python3 pygit.py merge branch-name
```

### Rebase Branches
```bash
python3 pygit.py rebase target-branch
```

### Clean Untracked Files
```bash
python3 pygit.py clean -f
```

### Set Configuration
```bash
python3 pygit.py config user.name "Your Name"
python3 pygit.py config user.email "your.email@example.com"
```

## Project Structure

- `pygit.py`: Main entry point for the command-line interface
- `pygit/`: Package containing the core functionality
  - `__init__.py`: Package initialization
  - `commands.py`: Implementation of all PyGit commands
  - `config.py`: Configuration handling
  - `diff.py`: File and tree comparison
  - `index.py`: Staging area management
  - `objects.py`: Object storage and retrieval
  - `refs.py`: Reference management (branches, tags)
  - `repository.py`: Repository initialization and location
  - `resolver.py`: Reference resolution
  - `utils.py`: Utility functions

## Testing

PyGit comes with a comprehensive test suite that covers all major functionality. See [README_TESTS.md](README_TESTS.md) for details on running the tests.


## Acknowledgements

PyGit is inspired by Git, created by Linus Torvalds. It aims to provide a simplified implementation for educational purposes while maintaining compatibility with the core Git workflow.
