import sys
from pygit import commands
from pygit.repository import find_pygit_dir

def main():
    if find_pygit_dir() is None and len(sys.argv) > 1 and sys.argv[1] != 'init':
        print("fatal: not a pygit repository (or any of the parent directories): .pygit", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 1:
        print("usage: pygit.py <command> [<args>]", file=sys.stderr)
        sys.exit(1)

    command_name = sys.argv[1]
    command_args = sys.argv[2:]
    command_func = getattr(commands, command_name, None)
    if command_func:
        try:
            command_func(*command_args)
        except TypeError:
            print(f"Error: Invalid arguments for command '{command_name}'", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: Unknown command '{command_name}'", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()