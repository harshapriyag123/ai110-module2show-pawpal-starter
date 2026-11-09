"""Round-trip, schema, and failed-write tests for durable household storage."""

from copy import deepcopy
from datetime import date
import json

import pytest

from main import create_demo_owner
from pawpal_system import MAX_JSON_BYTES, Owner, Scheduler

DAY = date(2026, 11, 9)


def test_round_trip_restores_all_pets_tasks_history_and_schedule(tmp_path):
    owner = create_demo_owner(DAY)
    pet = owner.pets[0]
    walk = next(task for task in pet.tasks if task.description == "Morning walk")
    following = pet.mark_task_complete(walk.id)
    path = tmp_path / "nested" / "data.json"
    owner.save_to_json(path)
    restored = Owner.load_from_json(path)
    assert restored == owner and restored is not owner
    assert restored.pets[0] is not pet
    assert restored.pets[0].get_task(walk.id).completed
    assert restored.pets[0].get_task(following.id).series_id == walk.series_id
    assert Scheduler(restored).generate_schedule(DAY) == Scheduler(owner).generate_schedule(DAY)
    restored.pets[0].mark_task_complete(walk.id)
    assert len(restored.pets[0].tasks) == 3


def test_empty_household_and_unicode_round_trip():
    owner = Owner("Harsha 🐾")
    encoded = owner.to_json()
    assert "🐾" in encoded
    assert Owner.from_json(encoded.encode("utf-8")) == owner
    assert Owner.from_dict(owner.to_dict()) == owner


@pytest.mark.parametrize("encoded", ["{broken", "null", "[]", "{}", b"\xff"])
def test_invalid_json_or_root_schema_is_rejected(encoded):
    with pytest.raises(ValueError):
        Owner.from_json(encoded)


@pytest.mark.parametrize("version", [2, True, "1"])
def test_unknown_schema_versions_are_rejected(version):
    data = Owner("Jordan").to_dict()
    data["schema_version"] = version
    with pytest.raises(ValueError, match="version"):
        Owner.from_dict(data)


@pytest.mark.parametrize("change", [
    lambda data: data["owner"].update(name=7),
    lambda data: data["owner"].update(pets={}),
    lambda data: data["owner"]["pets"][0].update(tasks={}),
    lambda data: data["owner"]["pets"][0].update(unexpected="field"),
    lambda data: data["owner"]["pets"][0]["tasks"][0].update(duration_minutes=0),
    lambda data: data["owner"]["pets"][0]["tasks"][0].update(completed="false"),
    lambda data: data["owner"]["pets"][0]["tasks"][0].update(due_date="not-a-date"),
    lambda data: data["owner"]["pets"][0]["tasks"][0].update(scheduled_time="25:00"),
])
def test_invalid_nested_data_is_rejected_before_restoring(change):
    data = create_demo_owner(DAY).to_dict()
    change(data)
    with pytest.raises(ValueError):
        Owner.from_dict(data)


def test_duplicate_task_identity_in_backup_is_rejected():
    data = create_demo_owner(DAY).to_dict()
    duplicate = deepcopy(data["owner"]["pets"][0]["tasks"][0])
    data["owner"]["pets"][1]["tasks"].append(duplicate)
    with pytest.raises(ValueError, match="exactly one pet"):
        Owner.from_dict(data)


@pytest.mark.parametrize("operation", ["fsync", "replace"])
def test_failed_atomic_save_preserves_previous_file_and_cleans_temporary_files(tmp_path, monkeypatch, operation):
    path = tmp_path / "data.json"
    original = Owner("Original")
    original.save_to_json(path)
    before = path.read_bytes()

    def fail(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(f"pawpal_system.os.{operation}", fail)
    with pytest.raises(OSError, match="disk failure"):
        Owner("Changed").save_to_json(path)
    assert path.read_bytes() == before
    assert list(tmp_path.glob(".*.tmp")) == []


def test_missing_corrupt_and_oversized_files_are_rejected(tmp_path):
    path = tmp_path / "data.json"
    with pytest.raises(FileNotFoundError):
        Owner.load_from_json(path)
    path.write_text("broken")
    with pytest.raises(ValueError):
        Owner.load_from_json(path)
    assert path.read_text() == "broken"
    path.write_bytes(b" " * (MAX_JSON_BYTES + 1))
    with pytest.raises(ValueError, match="2 MB"):
        Owner.load_from_json(path)
    with pytest.raises(ValueError, match="2 MB"):
        Owner.from_json(path.read_bytes())


def test_oversized_save_does_not_replace_existing_file(tmp_path):
    path = tmp_path / "data.json"
    Owner("Original").save_to_json(path)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="2 MB"):
        Owner("x" * MAX_JSON_BYTES).save_to_json(path)
    assert path.read_bytes() == before
