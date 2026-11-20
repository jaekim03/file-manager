from __future__ import annotations

import argparse
from pathlib import Path


def resolve_target(path: str | None) -> Path:
    """Folder to organize: the given path, or the current folder."""
    return Path(path).expanduser().resolve() if path else Path.cwd().resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="organize", description="Sort loose files into an NN_Category tree."
    )
    parser.add_argument(
        "path", nargs="?", help="folder to organize (default: current folder)"
    )
    args = parser.parse_args(argv)

    target = resolve_target(args.path)
    print(f"Would organize: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
