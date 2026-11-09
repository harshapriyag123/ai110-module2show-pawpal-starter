"""Verify that the standalone demo exercises the required algorithmic behaviors."""

from main import main
from datetime import date
from pathlib import Path
import subprocess
import sys

import pytest

from pawpal_system import Owner


def test_cli_demo(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["main.py", "--date", "2026-11-09"])
    main()
    output = capsys.readouterr().out
    assert "Today's Schedule | 2026-11-09" in output
    assert "Mochi (dog), Luna (cat)" in output
    assert "WARNING: Morning walk overlaps Breakfast." in output
    assert "Care budget: 60/75 minutes" in output
    assert "new daily task: 2026-11-10" in output
    assert "Next free 15-minute slot from 08:00: 08:30" in output


def test_save_and_load_in_separate_cli_processes(tmp_path):
    path = tmp_path / "data.json"
    script = Path(__file__).resolve().parents[1] / "main.py"
    saved = subprocess.check_output([sys.executable, str(script), "--date", "2026-11-09", "--save", str(path)], text=True)
    assert "Saved household:" in saved
    before = Owner.load_from_json(path)
    assert len(before.pets) == 2 and len(before.get_all_tasks()) == 6
    reopened = subprocess.check_output([sys.executable, str(script), "--date", "2026-11-09", "--load", str(path)], text=True)
    assert "Mochi (dog), Luna (cat)" in reopened
    assert Owner.load_from_json(path) == before  # Loading a saved household is read-only.


def test_loading_empty_household_does_not_require_scheduled_tasks(tmp_path, monkeypatch, capsys):
    path = tmp_path / "empty.json"
    Owner("Empty household").save_to_json(path)
    monkeypatch.setattr("sys.argv", ["main.py", "--load", str(path), "--date", "2026-11-09"])
    main()
    assert "Care budget: 0/120 minutes" in capsys.readouterr().out


def test_cli_reports_invalid_saved_file(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text("broken")
    monkeypatch.setattr("sys.argv", ["main.py", "--load", str(path)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
