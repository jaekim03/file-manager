from file_manager.cli import main


def test_no_argument_targets_current_folder(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert main([]) == 0

    assert capsys.readouterr().out.strip() == f"Would organize: {tmp_path.resolve()}"


def test_argument_targets_given_folder(tmp_path, capsys):
    assert main([str(tmp_path)]) == 0

    assert capsys.readouterr().out.strip() == f"Would organize: {tmp_path.resolve()}"
