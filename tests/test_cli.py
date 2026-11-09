"""Verify that the standalone demo exercises the required algorithmic behaviors."""

from main import main


def test_cli_demo(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["main.py", "--date", "2026-11-09"])
    main()
    output = capsys.readouterr().out
    assert "Today's Schedule | 2026-11-09" in output
    assert "Mochi (dog), Luna (cat)" in output
    assert "WARNING: Morning walk overlaps Breakfast." in output
    assert "Care budget: 60/75 minutes" in output
    assert "new daily task: 2026-11-10" in output
