# Development

How the repo is set up, what to build next, and how to write tests. For what the tool does, see [design.md](design.md).

## Current state

Slice 1 (scaffold) is done. The package installs, `organize` runs, and the tests pass. Nothing is sorted yet: `organize` only prints the folder it would sort.

| File | Contents |
|---|---|
| `README.md` | Planned use, safety, privacy |
| `docs/design.md` | v0 design |
| `docs/development.md` | This file |
| `pyproject.toml` | Name `file-manager` 0.1.0, Python >= 3.9, no runtime dependencies. setuptools build, `dev` extra with `pytest`, `organize` command, pytest reads `tests/`. |
| `src/file_manager/__init__.py` | Package version |
| `src/file_manager/cli.py` | `organize [path]`: targets the given path, or the current folder if none, and prints `Would organize: <folder>` |
| `tests/test_cli.py` | `test_no_argument_targets_current_folder`, `test_argument_targets_given_folder` |
| `.gitignore` | Python and macOS ignores (includes `.venv/`) |
| `LICENSE` | MIT |

**Not set up yet:** the safety checks, moving files, Trash, logging, undo, models, settings, CI and the Claude Code plugin manifest.

### Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip   # macOS Python 3.9's bundled pip is too old for editable installs
pip install -e ".[dev]"
pytest                                # 2 passed
organize                              # Would organize: <current folder>
```

## What we did

**2026-11-20**
- Added this doc.
- Command changed to `organize [path]`, which defaults to the current folder.
- Scaffold: package, `organize` stub, 2 CLI tests (passing). pip needed an upgrade to install.

## Next steps

Build in thin slices. Each slice ends with code that runs, has passing tests and is committed. The core comes first because both front ends depend on it.

1. ~~**Scaffold.**~~ Done. See Current state.
2. **Plan model.** A dataclass for one action that matches the JSON in design §2, plus code to parse and validate the model's output.
3. **Safety checks** (design §3, §5):
   - every source is inside the source folder
   - every destination is inside the destination root
   - hidden files, partial downloads and symlinks are skipped
   - one bad action rejects the whole plan
4. **Executor.** Move files without ever overwriting: add `_2` when a different file has the same name, and leave the source in place when an identical file is already there. Send `trash_patterns` matches to the Trash and write a JSON log of the run.
5. **Undo.** Reverse the last run from its log.
6. **Scanner and test fixtures.** List the files in the source folder. Add the fake model and the script that builds a fake folder to sort (design §6).
7. **Standalone CLI.** `organize [path]` with `--dry-run` and `--undo`, plus settings in `~/.config/file-manager/`.
8. **Claude Code plugin.** `/file-manager:organize [path]`, using the shared prompt.
9. **Real model providers.** API key and local model.

Record design changes in the decision log in design §7.

## Writing tests

**Tool.** Use pytest. Its built-in `tmp_path` fixture gives each test a fresh temporary folder, so no test touches real files.

**Loop.** For each rule in the design:

1. Write a test that states the rule. Run it and watch it fail.
2. Write the smallest code that makes it pass.
3. Clean up the code while the tests stay green.
4. Commit.

**Layout.**

- One test file per module: `tests/test_<module>.py`.
- One behavior per test, with the behavior in the name, for example `test_move_never_overwrites`.
- Each test follows arrange, act, assert: build a fake folder tree in `tmp_path`, call the function, then check the filesystem and the log.

**No real model.** Tests use the fake model, which returns canned answers, so the full flow runs offline with no API key.

**Example**

```python
# tests/test_executor.py
from file_manager.executor import move_file


def test_move_never_overwrites(tmp_path):
    # Arrange: a destination that already holds a different file with the same name
    src = tmp_path / "Downloads" / "report.pdf"
    src.parent.mkdir()
    src.write_text("new")
    dest_dir = tmp_path / "root" / "00_Personal"
    dest_dir.mkdir(parents=True)
    (dest_dir / "report.pdf").write_text("old")

    # Act
    result = move_file(src, dest_dir)

    # Assert: the original is untouched and the new file gets a _2 suffix
    assert (dest_dir / "report.pdf").read_text() == "old"
    assert result == dest_dir / "report_2.pdf"
    assert result.read_text() == "new"
    assert not src.exists()
```

**Running tests**

```sh
pytest              # all tests
pytest -k undo      # tests whose names contain "undo"
pytest -x           # stop at the first failure
```

Once there is real code, add `pytest-cov` and run `pytest --cov=file_manager` to see which code the tests don't cover.
