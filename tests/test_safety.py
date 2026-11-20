import pytest

from file_manager.plan import Action
from file_manager.safety import UnsafePlanError, check_plan, is_protected


def action(file="report.pdf", dest="00_Personal", new_name="2026-10-31_report.pdf"):
    return Action(
        file=file, dest=dest, new_name=new_name, confidence="high", reason="test"
    )


@pytest.fixture
def folders(tmp_path):
    """A source folder holding report.pdf, and an empty destination root."""
    source = tmp_path / "Downloads"
    source.mkdir()
    (source / "report.pdf").write_text("report")
    root = tmp_path / "root"
    root.mkdir()
    return source, root


def check(folders, *actions):
    source, root = folders
    check_plan(list(actions), source, root)


# Safe plans


def test_safe_plan_passes(folders):
    check(folders, action())


def test_empty_plan_passes(folders):
    check(folders)


def test_nested_destination_passes(folders):
    check(folders, action(dest="00_Personal/01_Financial"))


def test_destination_that_does_not_exist_yet_passes(folders):
    check(folders, action(dest="05_New"))


# Source must be a file directly inside the source folder


@pytest.mark.parametrize("file", ["../report.pdf", "/etc/passwd", "sub/report.pdf"])
def test_rejects_source_outside_source_folder(folders, file):
    with pytest.raises(UnsafePlanError, match="source folder"):
        check(folders, action(file=file))


@pytest.mark.parametrize("file", [".", ".."])
def test_rejects_dot_paths_as_source(folders, file):
    with pytest.raises(UnsafePlanError):
        check(folders, action(file=file))


def test_rejects_missing_source(folders):
    with pytest.raises(UnsafePlanError, match="does not exist"):
        check(folders, action(file="missing.pdf"))


def test_rejects_folder_as_source(folders):
    source, _ = folders
    (source / "Photos").mkdir()

    with pytest.raises(UnsafePlanError, match="not a file"):
        check(folders, action(file="Photos"))


# Destination must be inside the destination root


@pytest.mark.parametrize("dest", ["../elsewhere", "00_Personal/../../elsewhere"])
def test_rejects_destination_escaping_root(folders, dest):
    with pytest.raises(UnsafePlanError, match="destination root"):
        check(folders, action(dest=dest))


def test_rejects_absolute_destination(folders, tmp_path):
    with pytest.raises(UnsafePlanError, match="destination root"):
        check(folders, action(dest=str(tmp_path / "elsewhere")))


def test_rejects_destination_through_symlink_leading_outside(folders, tmp_path):
    _, root = folders
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "00_Link").symlink_to(outside)

    with pytest.raises(UnsafePlanError, match="destination root"):
        check(folders, action(dest="00_Link"))


# New name must be a plain, visible filename


@pytest.mark.parametrize("new_name", ["a/b.pdf", "../b.pdf", "/tmp/b.pdf", ".", ".."])
def test_rejects_new_name_that_is_a_path(folders, new_name):
    with pytest.raises(UnsafePlanError, match="new name"):
        check(folders, action(new_name=new_name))


def test_rejects_hidden_new_name(folders):
    with pytest.raises(UnsafePlanError, match="new name"):
        check(folders, action(new_name=".report.pdf"))


# Hidden files, partial downloads and symlinks are never touched


@pytest.mark.parametrize(
    "name",
    [".DS_Store", ".hidden.pdf", "movie.mp4.crdownload", "file.zip.part", "a.download"],
)
def test_rejects_protected_files(folders, name):
    source, _ = folders
    (source / name).write_text("x")

    with pytest.raises(UnsafePlanError, match="never touched"):
        check(folders, action(file=name))


def test_rejects_symlink_source(folders, tmp_path):
    source, _ = folders
    target = tmp_path / "target.pdf"
    target.write_text("x")
    (source / "link.pdf").symlink_to(target)

    with pytest.raises(UnsafePlanError, match="never touched"):
        check(folders, action(file="link.pdf"))


def test_is_protected(tmp_path):
    (tmp_path / "ok.pdf").write_text("x")
    (tmp_path / ".hidden").write_text("x")
    (tmp_path / "big.iso.crdownload").write_text("x")
    (tmp_path / "link.pdf").symlink_to(tmp_path / "ok.pdf")

    assert not is_protected(tmp_path / "ok.pdf")
    assert is_protected(tmp_path / ".hidden")
    assert is_protected(tmp_path / "big.iso.crdownload")
    assert is_protected(tmp_path / "link.pdf")


# Whole plan


def test_rejects_same_file_twice(folders):
    with pytest.raises(UnsafePlanError, match="more than once"):
        check(folders, action(), action(dest="01_Work"))


def test_one_bad_action_rejects_whole_plan_and_names_it(folders):
    source, _ = folders
    (source / "b.pdf").write_text("b")

    with pytest.raises(UnsafePlanError, match="action 1"):
        check(folders, action(), action(file="b.pdf", dest="../escape"))
