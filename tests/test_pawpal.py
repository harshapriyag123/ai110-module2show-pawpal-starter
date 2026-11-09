"""Behavioral tests for the models, recurrence, and scheduling constraints."""

from dataclasses import replace
from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

DAY = date(2026, 11, 9)


def care(title="Walk", at=time(8), **kwargs):
    return Task(title, at, due_date=DAY, **kwargs)


def household(*tasks, budget=120, start=time(6), end=time(22)):
    pet = Pet("Mochi", "dog", list(tasks))
    owner = Owner("Jordan", [pet], budget, start, end)
    return owner, pet, Scheduler(owner)


def test_mark_complete_changes_status():
    task = care()
    assert not task.completed
    assert task.mark_complete() is None
    assert task.completed


def test_task_addition_increases_count():
    pet = Pet("Luna", "cat")
    pet.add_task(care())
    assert len(pet.tasks) == 1


@pytest.mark.parametrize("frequency,days", [("daily", 1), ("weekly", 7)])
@pytest.mark.parametrize("day", [DAY, date(2026, 12, 31), date(2028, 2, 28)])
def test_completion_creates_distinct_next_occurrence(frequency, days, day):
    task = Task("Feed", time(9), frequency=frequency, due_date=day)
    pet = Pet("Luna", "cat", [task])
    following = pet.mark_task_complete(task.id)
    assert following in pet.tasks and len(pet.tasks) == 2
    assert following.id != task.id and following.series_id == task.series_id
    assert following.due_date == day + timedelta(days=days)
    assert following.scheduled_time == task.scheduled_time
    assert following.frequency == frequency and not following.completed
    assert task.completed and task.due_date == day
    assert pet.mark_task_complete(task.id) is None
    assert len(pet.tasks) == 2


def test_undo_and_recomplete_does_not_duplicate_future_task():
    task = care(frequency="daily")
    _, pet, _ = household(task)
    following = pet.mark_task_complete(task.id)
    pet.mark_task_incomplete(task.id)
    assert not task.completed
    assert pet.mark_task_complete(task.id) is following
    assert len(pet.tasks) == 2


def test_direct_completion_returns_new_task_instance():
    task = care(frequency="daily")
    following = task.mark_complete()
    assert task.completed
    assert following is not task and following.due_date == DAY + timedelta(days=1)


def test_one_time_completion_does_not_repeat():
    task = care()
    _, pet, _ = household(task)
    assert pet.mark_task_complete(task.id) is None
    assert len(pet.tasks) == 1


def test_generated_occurrence_is_visible_to_owner_scheduler():
    task = care(frequency="daily")
    _, pet, scheduler = household(task)
    following = pet.mark_task_complete(task.id)
    assert scheduler.generate_schedule(DAY).scheduled == []
    assert scheduler.generate_schedule(DAY + timedelta(days=1)).scheduled == [(pet, following)]


def test_sort_is_chronological_and_does_not_mutate_source():
    late, early, middle = care("Late", time(18)), care("Early", time(8)), care("Middle", time(12))
    owner, pet, scheduler = household(late, early, middle)
    assert [task for _, task in scheduler.sort_by_time()] == [early, middle, late]
    assert pet.tasks == [late, early, middle]
    assert len(owner.get_all_tasks()) == 3
    assert scheduler.sort_by_time([]) == []


def test_sort_includes_date_before_time():
    later_day = replace(care("Tomorrow", time(7)), due_date=DAY + timedelta(days=1))
    today = care("Today", time(18))
    _, _, scheduler = household(later_day, today)
    assert [task for _, task in scheduler.sort_by_time()] == [today, later_day]


def test_filter_by_pet_name_id_status_and_date():
    pending, done = care("Feed"), care("Brush", time(10), completed=True)
    owner, pet, scheduler = household(pending, done)
    second = Pet("Luna", "cat", [care("Feed cat", time(12))])
    owner.add_pet(second)
    assert scheduler.filter_tasks(pet_name="MOCHI", completed=False) == [(pet, pending)]
    assert scheduler.filter_tasks(pet_id=pet.id, completed=True, on_date=DAY) == [(pet, done)]
    assert scheduler.filter_tasks(pet_id="absent") == []
    assert scheduler.filter_tasks(on_date=DAY + timedelta(days=1)) == []


def test_scheduler_reads_every_pet_through_owner_method(monkeypatch):
    owner = Owner("Jordan")
    first, second = Pet("Mochi", "dog"), Pet("Luna", "cat")
    one, two = care("Walk"), care("Feed", time(9))
    calls = []

    def all_tasks():
        calls.append(True)
        return [(first, one), (second, two)]

    monkeypatch.setattr(owner, "get_all_tasks", all_tasks)
    assert Scheduler(owner).generate_schedule(DAY).scheduled == [(first, one), (second, two)]
    assert calls


def test_priority_selects_later_high_task_before_early_low_when_budget_tight():
    low = care("Groom", time(8), duration_minutes=30, priority="low")
    high = care("Feed", time(10), duration_minutes=30, priority="high")
    _, pet, scheduler = household(low, high, budget=30)
    plan = scheduler.generate_schedule(DAY)
    assert plan.scheduled == [(pet, high)]
    assert plan.skipped[0][1] is low and "budget" in plan.skipped[0][2]
    assert plan.total_minutes == 30


def test_returned_plan_is_chronological_after_priority_selection():
    low, high = care("Play", time(8), priority="low"), care("Feed", time(10), priority="high")
    _, _, scheduler = household(high, low)
    assert [task for _, task in scheduler.generate_schedule(DAY).scheduled] == [low, high]


@pytest.mark.parametrize("second_time,expected", [(time(8), 1), (time(8, 10), 1), (time(8, 15), 0)])
def test_exact_overlap_and_adjacent_intervals(second_time, expected):
    _, _, scheduler = household(care("Walk"), care("Feed", second_time))
    assert len(scheduler.detect_conflicts(DAY)) == expected
    plan = scheduler.generate_schedule(DAY)
    assert len(plan.scheduled) == 2 - expected


def test_conflicts_across_pets_choose_high_priority_and_explain():
    low = care("Brush", priority="low", duration_minutes=30)
    owner, _, scheduler = household(low)
    high = care("Feed", time(8, 10), priority="high")
    cat = Pet("Luna", "cat", [high])
    owner.add_pet(cat)
    assert scheduler.detect_conflicts(DAY) == [(low, high)]
    plan = scheduler.generate_schedule(DAY)
    assert plan.scheduled == [(cat, high)]
    assert "Luna: Feed" in plan.skipped[0][2]


def test_conflicts_ignore_completed_and_different_date_tasks():
    first = care()
    done = care("Done", completed=True)
    future = replace(care("Future"), due_date=DAY + timedelta(days=1))
    _, _, scheduler = household(first, done, future)
    assert scheduler.detect_conflicts(DAY) == []
    assert not scheduler._overlap(first, future)


def test_budget_skips_large_task_but_still_fits_later_small_task():
    large, small = care("Long", duration_minutes=60), care("Short", time(10), duration_minutes=10)
    _, pet, scheduler = household(large, small, budget=10)
    assert scheduler.generate_schedule(DAY).scheduled == [(pet, small)]


def test_availability_checks_whole_task_and_accepts_exact_boundaries():
    before, inside = care("Before", time(6, 59)), care("Inside", time(7), duration_minutes=30)
    end, beyond = care("End", time(8, 45)), care("Beyond", time(8, 46))
    _, _, scheduler = household(before, inside, end, beyond, start=time(7), end=time(9))
    plan = scheduler.generate_schedule(DAY)
    assert [task for _, task in plan.scheduled] == [inside, end]
    assert len(plan.skipped) == 2
    assert all("hours" in reason for _, _, reason in plan.skipped)


def test_zero_budget_and_empty_household_are_valid():
    _, _, scheduler = household(care(), budget=0)
    assert scheduler.generate_schedule(DAY).scheduled == []
    assert Scheduler(Owner("Jordan")).generate_schedule(DAY).total_minutes == 0
    _, _, empty = household()
    assert empty.generate_schedule(DAY).to_rows() == []


def test_deterministic_ties_and_no_scheduling_mutations():
    first, second = care("First"), care("Second")
    owner, _, scheduler = household(first, second)
    first_plan = scheduler.generate_schedule(DAY)
    assert first_plan == scheduler.generate_schedule(DAY)
    assert first_plan.scheduled[0][1] is first
    assert not any(task.completed for _, task in owner.get_all_tasks())


def test_rows_include_readable_reason_and_end_time():
    _, _, scheduler = household(care(duration_minutes=30, priority="high"))
    row = scheduler.generate_schedule(DAY).to_rows()[0]
    assert row["Time"] == "08:00–08:30"
    assert row["Minutes"] == 30 and "High priority" in row["Why"]


def test_edit_and_remove_use_ids_with_duplicate_descriptions():
    first, second = care("Feed"), care("Feed", time(9))
    _, pet, _ = household(first, second)
    edited = pet.update_task(first.id, description="Breakfast", priority="high")
    assert edited.id == first.id and edited.priority == "high"
    assert pet.tasks[1] is second
    pet.remove_task(first.id)
    assert pet.tasks == [second]


def test_invalid_edit_leaves_original_intact():
    task = care()
    _, pet, _ = household(task)
    with pytest.raises(ValueError):
        pet.update_task(task.id, duration_minutes=0)
    assert pet.tasks == [task] and pet.tasks[0] is task
    with pytest.raises(ValueError):
        pet.update_task(task.id, id="replacement")
    task.mark_complete()
    with pytest.raises(ValueError):
        pet.update_task(task.id, description="Change history")


@pytest.mark.parametrize("method", ["get_task", "remove_task", "mark_task_complete", "mark_task_incomplete", "update_task"])
def test_missing_task_errors(method):
    with pytest.raises(ValueError, match="not found"):
        getattr(Pet("Luna", "cat"), method)("missing")


@pytest.mark.parametrize("changes", [
    {"description": " "}, {"duration_minutes": 0}, {"duration_minutes": -1},
    {"duration_minutes": True}, {"duration_minutes": 3.5}, {"duration_minutes": 1441},
    {"priority": "urgent"}, {"frequency": "monthly"}, {"due_date": "2026-11-09"},
    {"completed": "yes"}, {"scheduled_time": time(23, 59), "duration_minutes": 2},
    {"scheduled_time": time(8, 0, 30)}, {"scheduled_time": "08:00"},
])
def test_invalid_task_data_is_rejected(changes):
    with pytest.raises(ValueError):
        Task(**{"description": "Feed", "scheduled_time": time(8), **changes})


@pytest.mark.parametrize("changes", [
    {"name": " "}, {"available_minutes": -1}, {"available_minutes": 1441},
    {"available_minutes": True}, {"day_start": time(22), "day_end": time(6)},
    {"day_start": time(8), "day_end": time(8)},
])
def test_invalid_owner_preferences(changes):
    with pytest.raises(ValueError):
        Owner(**{"name": "Jordan", **changes})


def test_duplicate_ids_and_shared_task_objects_are_rejected():
    task = care()
    owner, pet, _ = household(task)
    with pytest.raises(ValueError):
        pet.add_task(task)
    with pytest.raises(ValueError):
        owner.add_pet(pet)
    with pytest.raises(ValueError):
        owner.add_pet(Pet("Luna", "cat", [task]))
    assert len(owner.pets) == 1
    with pytest.raises(ValueError):
        Pet("Mochi", "dog", [task, task])


@pytest.mark.parametrize("name,species", [(" ", "dog"), ("Mochi", " ")])
def test_blank_pet_details(name, species):
    with pytest.raises(ValueError):
        Pet(name, species)


def test_defaults_are_independent_and_labels_normalized():
    first, second = Pet("Mochi", "Dog"), Pet("Luna", "Cat")
    first.add_task(care(priority=" HIGH ", frequency=" DAILY "))
    assert second.tasks == [] and first.species == "dog"
    assert first.tasks[0].priority == "high" and first.tasks[0].frequency == "daily"


def test_default_plan_date_is_today():
    owner = Owner("Jordan", [Pet("Mochi", "dog", [Task("Walk", time(8))])])
    assert len(Scheduler(owner).generate_schedule().scheduled) == 1
