import pytest

from rightsflow.cli import main


def test_generate_without_key_has_clean_cli_error(monkeypatch, capsys):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        main(["generate", "--prompt", "test music"])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "pass --mock" in captured.err
    assert "Traceback" not in captured.err
