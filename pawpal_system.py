"""Initial class skeleton translated from diagrams/uml_draft.mmd."""

from dataclasses import dataclass, field
from datetime import date, time
from uuid import uuid4


@dataclass
class Task:
    description: str
    scheduled_time: time
    duration_minutes: int = 15
    priority: str = "medium"
    frequency: str = "daily"
    start_date: date = field(default_factory=date.today)
    id: str = field(default_factory=lambda: uuid4().hex)
    completed_dates: set[date] = field(default_factory=set)

    def is_due(self, on_date: date) -> bool:
        """Check whether the task occurs on the requested date."""
        raise NotImplementedError

    def mark_complete(self, on_date: date | None = None) -> None:
        """Record completion for one occurrence."""
        raise NotImplementedError


@dataclass
class Pet:
    name: str
    species: str
    tasks: list[Task] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid4().hex)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        raise NotImplementedError


@dataclass
class Owner:
    name: str
    pets: list[Pet] = field(default_factory=list)
    available_minutes: int = 120
    day_start: time = time(6)
    day_end: time = time(22)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        raise NotImplementedError

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Collect tasks from every pet, preserving their pet association."""
        raise NotImplementedError


@dataclass
class Scheduler:
    owner: Owner

    def generate_schedule(self, on_date: date):
        """Choose nonoverlapping due tasks within the owner's limits."""
        raise NotImplementedError
