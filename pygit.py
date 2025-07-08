#!/usr/bin/env python3

import sys
from pygit import commands
from pygit.repository import find_pygit_dir


def main():

    # Allow 'init' and 'clone' to run outside a repository
    if find_pygit_dir() is None and len(sys.argv) > 1 and sys.argv[1] not in ['init', 'clone']:
        print("fatal: not a pygit repository (or any of the parent directories): .pygit", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: pygit.py <command> [<args>]", file=sys.stderr)
        sys.exit(1)

    command_name = sys.argv[1]
    command_args = sys.argv[2:]

    command_func = getattr(commands, command_name, None)

    if command_func:
        try:
            result = command_func(*command_args)
            if result is False:
                sys.exit(1)
        except TypeError as e:
            print(f"Error: Invalid arguments for command '{command_name}'. Details: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"pygit: '{command_name}' is not a pygit command.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
