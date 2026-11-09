"""Exercise the gap-finding algorithm independently from priority selection."""

from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

DAY = date(2026, 11, 9)


def task(title, at, duration=30, **kwargs):
    return Task(title, at, duration_minutes=duration, due_date=DAY, **kwargs)


def test_empty_calendar_respects_hours_and_earliest_start():
    scheduler = Scheduler(Owner("Jordan", day_start=time(7), day_end=time(9)))
    assert scheduler.next_available_slot(DAY, 15) == time(7)
    assert scheduler.next_available_slot(DAY, 15, time(6)) == time(7)
    assert scheduler.next_available_slot(DAY, 15, time(8, 45)) == time(8, 45)
    assert scheduler.next_available_slot(DAY, 16, time(8, 45)) is None


def test_merges_overlaps_across_multiple_pets_without_mutation():
    walk = task("Walk", time(8), 30)
    feed = task("Feed", time(8, 15), 30)
    owner = Owner("Jordan", [Pet("Mochi", "dog", [walk]), Pet("Luna", "cat", [feed])])
    before = owner.to_dict()
    assert Scheduler(owner).next_available_slot(DAY, 15, time(8)) == time(8, 45)
    assert owner.to_dict() == before


def test_finds_gap_before_later_task_and_allows_adjacent_start():
    pet = Pet("Mochi", "dog", [task("Walk", time(8)), task("Play", time(9))])
    scheduler = Scheduler(Owner("Jordan", [pet]))
    assert scheduler.next_available_slot(DAY, 30, time(8)) == time(8, 30)
    assert scheduler.next_available_slot(DAY, 31, time(8)) == time(9, 30)


def test_ignores_completed_and_other_date_tasks_and_can_exclude_edited_task():
    done = task("Done", time(8), completed=True)
    tomorrow = Task("Tomorrow", time(8), due_date=DAY + timedelta(days=1))
    edited = task("Editing", time(8))
    scheduler = Scheduler(Owner("Jordan", [Pet("Mochi", "dog", [done, tomorrow, edited])]))
    assert scheduler.next_available_slot(DAY, 15, time(8)) == time(8, 30)
    assert scheduler.next_available_slot(DAY, 15, time(8), exclude_task_id=edited.id) == time(8)


def test_fully_occupied_window_has_no_available_slot():
    pet = Pet("Mochi", "dog", [task("Walk", time(8), 60)])
    scheduler = Scheduler(Owner("Jordan", [pet], day_start=time(8), day_end=time(9)))
    assert scheduler.next_available_slot(DAY, 1) is None
    assert scheduler.next_available_slot(DAY, 60, time(9)) is None


@pytest.mark.parametrize("duration", [0, -1, 1441, True, 2.5])
def test_rejects_invalid_slot_duration(duration):
    with pytest.raises(ValueError):
        Scheduler(Owner("Jordan")).next_available_slot(DAY, duration)
