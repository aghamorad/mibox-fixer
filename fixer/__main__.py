"""Entry point: `python -m fixer` opens the GUI, `python -m fixer --help` the CLI."""

import sys


def main() -> int:
    argv = sys.argv[1:]
    if argv:
        from .cli import main as cli_main

        return cli_main(argv)
    try:
        from .gui import main as gui_main
    except ImportError as exc:
        print(f"No graphical toolkit available ({exc}).", file=sys.stderr)
        print("Run `python -m fixer --help` to use the terminal version instead.", file=sys.stderr)
        return 2
    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
