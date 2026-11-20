"""Carry out a checked plan: move, rename, trash and log (design §3, §5)."""

from __future__ import annotations

import filecmp
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

from file_manager.plan import Action
from file_manager.safety import check_plan

DEFAULT_TRASH_PATTERNS = ("*.dmg", "*.pkg")
DEFAULT_TRASH_DIR = Path.home() / ".Trash"


@dataclass
class RunLog:
    """What one run did, in enough detail to undo it."""

    started: str
    source: str
    dest_root: str
    entries: list[dict] = field(default_factory=list)
    created_dirs: list[str] = field(default_factory=list)
    path: Path | None = None

    def to_dict(self) -> dict:
        return {
            "started": self.started,
            "source": self.source,
            "dest_root": self.dest_root,
            "entries": self.entries,
            "created_dirs": self.created_dirs,
        }


def matches_trash(name: str, patterns: tuple[str, ...] | list[str]) -> bool:
    """Whether a filename matches any trash pattern, ignoring case."""
    return any(fnmatch(name.lower(), p.lower()) for p in patterns)


def move_file(src: Path, dest_dir: Path, new_name: str | None = None) -> Path | None:
    """Move src into dest_dir without ever overwriting.

    A different file with the same name gets _2, _3, ... added. If an identical
    file is already there, src is left in place and None is returned.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = Path(new_name or src.name)

    for target in _candidates(dest_dir, name):
        if not target.exists() and not target.is_symlink():
            _move(src, target)
            return target
        if _same_content(src, target):
            return None
    raise AssertionError("unreachable")


def trash_file(src: Path, trash_dir: Path) -> Path:
    """Move src into the Trash folder, adding _2, _3, ... on a name clash."""
    trash_dir.mkdir(parents=True, exist_ok=True)
    for target in _candidates(trash_dir, Path(src.name)):
        if not target.exists() and not target.is_symlink():
            _move(src, target)
            return target
    raise AssertionError("unreachable")


def execute(
    actions: list[Action],
    source: Path,
    dest_root: Path,
    *,
    log_dir: Path,
    trash_patterns: tuple[str, ...] | list[str] = DEFAULT_TRASH_PATTERNS,
    trash_dir: Path | None = None,
) -> RunLog:
    """Check the plan, carry it out and write a JSON log. Returns the log."""
    check_plan(actions, source, dest_root)

    source = source.resolve()
    dest_root = dest_root.resolve()
    trash_dir = (trash_dir or DEFAULT_TRASH_DIR).resolve()
    now = datetime.now(timezone.utc)
    log = RunLog(started=now.isoformat(), source=str(source), dest_root=str(dest_root))

    for action in actions:
        src = source / action.file
        if matches_trash(action.file, trash_patterns):
            dst = trash_file(src, trash_dir)
            log.entries.append({"op": "trash", "src": str(src), "dst": str(dst)})
            continue

        dest_dir = (dest_root / action.dest).resolve()
        log.created_dirs.extend(str(d) for d in _missing_dirs(dest_dir, dest_root))
        dst = move_file(src, dest_dir, action.new_name)
        if dst is None:
            log.entries.append({"op": "skip_identical", "src": str(src), "dst": None})
        else:
            log.entries.append({"op": "move", "src": str(src), "dst": str(dst)})

    log_dir.mkdir(parents=True, exist_ok=True)
    log.path = log_dir / f"{now.strftime('%Y%m%dT%H%M%S_%fZ')}.json"
    log.path.write_text(json.dumps(log.to_dict(), indent=2) + "\n")
    return log


def _candidates(folder: Path, name: Path):
    """folder/name, then folder/stem_2.ext, folder/stem_3.ext, ..."""
    yield folder / name.name
    n = 2
    while True:
        yield folder / f"{name.stem}_{n}{name.suffix}"
        n += 1


def _same_content(a: Path, b: Path) -> bool:
    return (
        b.is_file()
        and not b.is_symlink()
        and a.stat().st_size == b.stat().st_size
        and filecmp.cmp(a, b, shallow=False)
    )


def _move(src: Path, target: Path) -> None:
    try:
        src.rename(target)
    except OSError:
        shutil.move(str(src), str(target))  # across volumes


def _missing_dirs(dest_dir: Path, dest_root: Path) -> list[Path]:
    """Folders between dest_root and dest_dir that don't exist yet, outermost first."""
    missing = []
    d = dest_dir
    while d != dest_root and not d.exists():
        missing.append(d)
        d = d.parent
    return list(reversed(missing))
