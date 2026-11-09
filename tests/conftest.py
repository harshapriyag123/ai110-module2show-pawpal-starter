"""Keep application persistence isolated between tests and away from real household data."""

import pytest


@pytest.fixture(autouse=True)
def isolated_household_file(monkeypatch, tmp_path):
    monkeypatch.setenv("PAWPAL_DATA_FILE", str(tmp_path / "app-household.json"))
