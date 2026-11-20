import json

import pytest

from file_manager.executor import execute, matches_trash, move_file, trash_file
from file_manager.plan import Action
from file_manager.safety import UnsafePlanError


def action(file="report.pdf", dest="00_Personal", new_name="2026-10-31_report.pdf"):
    return Action(
        file=file, dest=dest, new_name=new_name, confidence="high", reason="test"
    )


@pytest.fixture
def dirs(tmp_path):
    """Source, destination root, Trash and log folders, all inside tmp_path."""
    source = tmp_path / "Downloads"
    root = tmp_path / "root"
    trash = tmp_path / "Trash"
    logs = tmp_path / "logs"
    for d in (source, root, trash):
        d.mkdir()
    return source, root, trash, logs


def run(dirs, *actions):
    source, root, trash, logs = dirs
    return execute(list(actions), source, root, trash_dir=trash, log_dir=logs)


# move_file


def test_move_never_overwrites(tmp_path):
    src = tmp_path / "Downloads" / "report.pdf"
    src.parent.mkdir()
    src.write_text("new")
    dest_dir = tmp_path / "root" / "00_Personal"
    dest_dir.mkdir(parents=True)
    (dest_dir / "report.pdf").write_text("old")

    result = move_file(src, dest_dir)

    assert (dest_dir / "report.pdf").read_text() == "old"
    assert result == dest_dir / "report_2.pdf"
    assert result.read_text() == "new"
    assert not src.exists()


def test_move_into_empty_dest(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("a")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    result = move_file(src, dest_dir)

    assert result == dest_dir / "a.txt"
    assert result.read_text() == "a"
    assert not src.exists()


def test_move_creates_missing_dest_folders(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("a")
    dest_dir = tmp_path / "dest" / "nested" / "deeper"

    result = move_file(src, dest_dir)

    assert result == dest_dir / "a.txt"
    assert result.read_text() == "a"


def test_move_renames_to_new_name(tmp_path):
    src = tmp_path / "Scan 12.pdf"
    src.write_text("scan")
    dest_dir = tmp_path / "dest"

    result = move_file(src, dest_dir, "2026-10-31_bank_statement.pdf")

    assert result == dest_dir / "2026-10-31_bank_statement.pdf"
    assert result.read_text() == "scan"


def test_identical_file_leaves_source_in_place(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("same")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    (dest_dir / "a.txt").write_text("same")

    result = move_file(src, dest_dir)

    assert result is None
    assert src.read_text() == "same"
    assert sorted(p.name for p in dest_dir.iterdir()) == ["a.txt"]


def test_identical_file_under_suffixed_name_leaves_source(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("same")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    (dest_dir / "a.txt").write_text("different")
    (dest_dir / "a_2.txt").write_text("same")

    assert move_file(src, dest_dir) is None
    assert src.exists()


def test_second_collision_gets_3(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("third")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    (dest_dir / "a.txt").write_text("first")
    (dest_dir / "a_2.txt").write_text("second")

    result = move_file(src, dest_dir)

    assert result == dest_dir / "a_3.txt"
    assert (dest_dir / "a.txt").read_text() == "first"
    assert (dest_dir / "a_2.txt").read_text() == "second"


def test_collision_without_extension(tmp_path):
    src = tmp_path / "README"
    src.write_text("new")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    (dest_dir / "README").write_text("old")

    assert move_file(src, dest_dir) == dest_dir / "README_2"


# Trash


@pytest.mark.parametrize(
    "name, expected",
    [
        ("setup.dmg", True),
        ("Setup.DMG", True),
        ("installer.pkg", True),
        ("report.pdf", False),
        ("dmg.txt", False),
    ],
)
def test_matches_trash(name, expected):
    assert matches_trash(name, ("*.dmg", "*.pkg")) is expected


def test_trash_collision_gets_suffix(tmp_path):
    src = tmp_path / "setup.dmg"
    src.write_text("new")
    trash = tmp_path / "Trash"
    trash.mkdir()
    (trash / "setup.dmg").write_text("old")

    result = trash_file(src, trash)

    assert result == trash / "setup_2.dmg"
    assert (trash / "setup.dmg").read_text() == "old"
    assert not src.exists()


def test_trash_pattern_goes_to_trash(dirs):
    source, root, trash, _ = dirs
    (source / "Setup.DMG").write_text("installer")

    run(dirs, action(file="Setup.DMG", dest="09_Apps", new_name="setup.dmg"))

    assert (trash / "Setup.DMG").read_text() == "installer"
    assert not (source / "Setup.DMG").exists()
    assert not (root / "09_Apps").exists()


# execute


def test_execute_moves_files(dirs):
    source, root, _, _ = dirs
    (source / "report.pdf").write_text("report")

    run(dirs, action())

    assert (root / "00_Personal" / "2026-10-31_report.pdf").read_text() == "report"
    assert not (source / "report.pdf").exists()


def test_execute_rejects_unsafe_plan_and_moves_nothing(dirs):
    source, root, _, logs = dirs
    (source / "report.pdf").write_text("report")

    with pytest.raises(UnsafePlanError):
        run(dirs, action(), action(file="../etc/passwd"))

    assert (source / "report.pdf").exists()
    assert list(root.iterdir()) == []
    assert not logs.exists()


def test_execute_writes_log_with_every_entry(dirs):
    source, root, trash, logs = dirs
    (source / "report.pdf").write_text("report")
    (source / "setup.dmg").write_text("installer")

    log = run(dirs, action(), action(file="setup.dmg", new_name="setup.dmg"))

    [log_file] = logs.iterdir()
    assert log.path == log_file
    data = json.loads(log_file.read_text())
    assert data["source"] == str(source.resolve())
    assert data["dest_root"] == str(root.resolve())
    assert data["entries"] == [
        {
            "op": "move",
            "src": str(source.resolve() / "report.pdf"),
            "dst": str(root.resolve() / "00_Personal" / "2026-10-31_report.pdf"),
        },
        {
            "op": "trash",
            "src": str(source.resolve() / "setup.dmg"),
            "dst": str(trash.resolve() / "setup.dmg"),
        },
    ]


def test_log_records_created_dirs(dirs):
    source, root, _, _ = dirs
    (source / "report.pdf").write_text("report")
    (root / "00_Personal").mkdir()

    log = run(dirs, action(dest="00_Personal/01_Financial/2026"))

    assert log.created_dirs == [
        str(root.resolve() / "00_Personal" / "01_Financial"),
        str(root.resolve() / "00_Personal" / "01_Financial" / "2026"),
    ]
    data = json.loads(log.path.read_text())
    assert data["created_dirs"] == log.created_dirs


def test_skip_identical_is_logged(dirs):
    source, root, _, _ = dirs
    (source / "report.pdf").write_text("same")
    (root / "00_Personal").mkdir()
    (root / "00_Personal" / "2026-10-31_report.pdf").write_text("same")

    log = run(dirs, action())

    assert (source / "report.pdf").exists()
    assert log.entries == [
        {
            "op": "skip_identical",
            "src": str(source.resolve() / "report.pdf"),
            "dst": None,
        }
    ]


def test_empty_plan_writes_empty_log(dirs):
    log = run(dirs)

    assert log.entries == []
    assert log.path.exists()
