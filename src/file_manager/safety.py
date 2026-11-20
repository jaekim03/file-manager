"""Safety checks that every plan must pass before anything moves (design §3, §5)."""

from __future__ import annotations

from pathlib import Path

from file_manager.plan import Action

PARTIAL_DOWNLOAD_SUFFIXES = (".crdownload", ".part", ".download")


class UnsafePlanError(ValueError):
    """The plan contains an action that could touch something it must not."""


def is_protected(path: Path) -> bool:
    """Hidden files, partial downloads and symlinks are never touched."""
    return (
        path.name.startswith(".")
        or path.suffix.lower() in PARTIAL_DOWNLOAD_SUFFIXES
        or path.is_symlink()
    )


def check_plan(actions: list[Action], source: Path, dest_root: Path) -> None:
    """Raise UnsafePlanError if any action is unsafe. One bad action rejects all."""
    source = source.resolve()
    dest_root = dest_root.resolve()
    seen: set[str] = set()

    for index, action in enumerate(actions):
        problem = _problem(action, source, dest_root, seen)
        if problem:
            raise UnsafePlanError(f"action {index} ({action.file!r}): {problem}")
        seen.add(action.file)


def _problem(action: Action, source: Path, dest_root: Path, seen: set[str]) -> str:
    """What is wrong with one action, or an empty string if it is safe."""
    if not _is_plain_name(action.file):
        return "file must be directly inside the source folder"
    if action.file in seen:
        return "file appears more than once in the plan"

    file = source / action.file
    if is_protected(file):
        return "hidden files, partial downloads and symlinks are never touched"
    if not file.exists():
        return "file does not exist"
    if not file.is_file():
        return "not a file"

    dest = (dest_root / action.dest).resolve()
    if not dest.is_relative_to(dest_root):
        return "destination is outside the destination root"

    if not _is_plain_name(action.new_name) or action.new_name.startswith("."):
        return "new name must be a plain, visible filename"

    return ""


def _is_plain_name(name: str) -> bool:
    """A single filename with no folder parts, like 'report.pdf'."""
    return name not in ("", ".", "..") and Path(name).name == name
