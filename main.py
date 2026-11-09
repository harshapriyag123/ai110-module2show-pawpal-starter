"""Run the backend without Streamlit: python main.py --date 2026-11-09."""

import argparse
from datetime import date, time

from pawpal_system import Owner, Pet, Scheduler, Task


def create_demo_owner(on_date: date) -> Owner:
    """Build repeatable sample data with two pets and intentionally unordered tasks."""
    owner = Owner("Jordan", available_minutes=75, day_start=time(7), day_end=time(21))
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    mochi.add_task(Task("Playtime", time(18), 20, "medium", "daily", on_date))
    mochi.add_task(Task("Morning walk", time(8), 30, "high", "daily", on_date))
    luna.add_task(Task("Brush coat", time(19), 20, "low", "weekly", on_date))
    luna.add_task(Task("Breakfast", time(8), 10, "medium", "daily", on_date))
    luna.add_task(Task("Medication reminder", time(9), 10, "high", "daily", on_date))
    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner


def main() -> None:
    """Print sorting, filtering, conflict, planning, and recurrence demonstrations."""
    parser = argparse.ArgumentParser(description="PawPal+ multi-pet care planner")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD")
    args = parser.parse_args()
    owner = create_demo_owner(args.date)
    scheduler = Scheduler(owner)
    print(f"Today's Schedule | {args.date} | {owner.name}")
    print("Pets: " + ", ".join(f"{pet.name} ({pet.species})" for pet in owner.pets))
    print("All pending tasks, sorted by time:")
    for pet, task in scheduler.sort_by_time(scheduler.filter_tasks(on_date=args.date, completed=False)):
        print(f"  {task.scheduled_time:%H:%M} | {pet.name}: {task.description}")
    print("Luna's pending tasks: " + ", ".join(task.description for _, task in
          scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Luna", completed=False))))
    for first, second in scheduler.detect_conflicts(args.date):
        print(f"WARNING: {first.description} overlaps {second.description}.")
    print("Priority-based plan:")
    plan = scheduler.generate_schedule(args.date)
    for row in plan.to_rows():
        print(f"  {row['Time']} | {row['Pet']}: {row['Task']} | {row['Minutes']} min | {row['Priority']}")
    print(f"Care budget: {plan.total_minutes}/{owner.available_minutes} minutes")
    if plan.skipped:
        print("Needs attention:")
        for pet, task, reason in plan.skipped:
            print(f"  {pet.name}: {task.description} - {reason}")
    pet, task = plan.scheduled[0]
    following = pet.mark_task_complete(task.id)
    if following:
        print(f"Completed {task.description}; new {following.frequency} task: "
              f"{following.due_date} at {following.scheduled_time:%H:%M} (pending).")


if __name__ == "__main__":
    main()
