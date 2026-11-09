"""Pet care domain models and scheduling algorithms, independent of Streamlit."""

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from contextlib import suppress
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

PRIORITIES = ("high", "medium", "low")
FREQUENCIES = ("once", "daily", "weekly")
MAX_JSON_BYTES = 2_000_000


def _record(value: object, keys: set[str], label: str) -> dict:
    """Require an exact JSON object schema so malformed backups fail clearly."""
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"Invalid {label} fields.")
    return value


def _string_fields(record: dict, keys: tuple[str, ...]) -> None:
    """Reject JSON values that cannot represent textual model fields."""
    if any(not isinstance(record[key], str) for key in keys):
        raise ValueError("Names, identifiers, dates, and times must be strings.")


def _minutes(value: time) -> int:
    """Convert a local, minute-precision time to minutes after midnight."""
    if not isinstance(value, time) or value.tzinfo is not None or value.second or value.microsecond:
        raise ValueError("Use a local time with whole minutes.")
    return value.hour * 60 + value.minute


@dataclass
class Task:
    """One dated care activity; completing a routine creates its next occurrence."""

    description: str
    scheduled_time: time
    duration_minutes: int = 15
    priority: str = "medium"
    frequency: str = "once"
    due_date: date = field(default_factory=date.today)
    completed: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)
    series_id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        """Normalize labels and reject invalid task data before it enters a plan."""
        self.description = self.description.strip()
        self.priority = self.priority.strip().lower()
        self.frequency = self.frequency.strip().lower()
        if not self.description or not self.id or not self.series_id:
            raise ValueError("Task description and identifiers are required.")
        if type(self.duration_minutes) is not int or not 1 <= self.duration_minutes <= 1440:
            raise ValueError("Duration must be an integer from 1 to 1440 minutes.")
        if self.priority not in PRIORITIES:
            raise ValueError("Priority must be high, medium, or low.")
        if self.frequency not in FREQUENCIES:
            raise ValueError("Frequency must be once, daily, or weekly.")
        if type(self.due_date) is not date or type(self.completed) is not bool:
            raise ValueError("Use a date for the due date and a boolean completion status.")
        if _minutes(self.scheduled_time) + self.duration_minutes > 1440:
            raise ValueError("A task cannot continue past midnight.")

    def mark_complete(self) -> "Task | None":
        """Complete once and return a new pending daily/weekly occurrence, if needed."""
        if self.completed:
            return None
        self.completed = True
        if self.frequency == "once":
            return None
        days = 1 if self.frequency == "daily" else 7
        return replace(self, due_date=self.due_date + timedelta(days=days),
                       completed=False, id=uuid4().hex)

    def end_at(self) -> datetime:
        """Compute the occurrence's end datetime from its start and duration."""
        return datetime.combine(self.due_date, self.scheduled_time) + timedelta(minutes=self.duration_minutes)


@dataclass
class Pet:
    """A pet with independently stored care activities and recurrence history."""

    name: str
    species: str
    tasks: list[Task] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        """Validate pet details and copy its task collection."""
        self.name, self.species = self.name.strip(), self.species.strip().lower()
        self.tasks = list(self.tasks)
        if not self.name or not self.species or not self.id:
            raise ValueError("Pet name, species, and ID are required.")
        if len({task.id for task in self.tasks}) != len(self.tasks):
            raise ValueError("Task IDs must be unique within a pet.")

    def add_task(self, task: Task) -> None:
        """Attach one task, rejecting duplicate identifiers."""
        if any(existing.id == task.id for existing in self.tasks):
            raise ValueError("This task is already assigned to the pet.")
        self.tasks.append(task)

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by stable ID even when descriptions are duplicated."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise ValueError("Task not found.")

    def update_task(self, task_id: str, **changes) -> Task:
        """Validate an edit atomically without changing identity or completion history."""
        if {"id", "series_id", "completed"} & changes.keys():
            raise ValueError("Use completion methods to change status; identifiers cannot be edited.")
        original = self.get_task(task_id)
        if original.completed:
            raise ValueError("Undo completion before editing a completed task.")
        edited = replace(original, **changes)
        self.tasks[self.tasks.index(original)] = edited
        return edited

    def mark_task_complete(self, task_id: str) -> Task | None:
        """Complete a task and automatically attach its next occurrence once."""
        task = self.get_task(task_id)
        next_task = task.mark_complete()
        if next_task:
            existing = next((item for item in self.tasks
                             if item.series_id == next_task.series_id and item.due_date == next_task.due_date), None)
            if existing:
                return existing
            self.add_task(next_task)
        return next_task

    def mark_task_incomplete(self, task_id: str) -> None:
        """Undo completion while preserving any already generated future occurrence."""
        self.get_task(task_id).completed = False

    def remove_task(self, task_id: str) -> None:
        """Remove just one occurrence, leaving other dates in the series intact."""
        self.get_task(task_id)
        self.tasks = [task for task in self.tasks if task.id != task_id]


@dataclass
class Owner:
    """One person's pets, remaining care-time budget, and daily availability."""

    name: str
    pets: list[Pet] = field(default_factory=list)
    available_minutes: int = 120
    day_start: time = time(6)
    day_end: time = time(22)

    def __post_init__(self) -> None:
        """Normalize the owner name and validate the initial household."""
        self.name = self.name.strip()
        self.pets = list(self.pets)
        self.validate()

    def validate(self) -> None:
        """Reject invalid budgets, availability windows, or shared identifiers."""
        if not self.name:
            raise ValueError("Owner name is required.")
        if type(self.available_minutes) is not int or not 0 <= self.available_minutes <= 1440:
            raise ValueError("Available time must be an integer from 0 to 1440 minutes.")
        if _minutes(self.day_start) >= _minutes(self.day_end):
            raise ValueError("Availability end must be later than start on the same day.")
        if len({pet.id for pet in self.pets}) != len(self.pets):
            raise ValueError("Pet IDs must be unique.")
        ids = [task.id for pet in self.pets for task in pet.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("Each task must belong to exactly one pet.")

    def add_pet(self, pet: Pet) -> None:
        """Register a pet after validating the combined household."""
        replace(self, pets=[*self.pets, pet])
        self.pets.append(pet)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Collect every pet's tasks with their pet association for the scheduler."""
        self.validate()
        return [(pet, task) for pet in self.pets for task in pet.tasks]

    def to_dict(self) -> dict:
        """Serialize the entire household, including task identity and recurrence history."""
        self.validate()
        return {"schema_version": 1, "owner": {
            "name": self.name, "available_minutes": self.available_minutes,
            "day_start": self.day_start.isoformat(timespec="minutes"),
            "day_end": self.day_end.isoformat(timespec="minutes"),
            "pets": [{"id": pet.id, "name": pet.name, "species": pet.species,
                      "tasks": [{"id": task.id, "series_id": task.series_id,
                                 "description": task.description,
                                 "scheduled_time": task.scheduled_time.isoformat(timespec="minutes"),
                                 "due_date": task.due_date.isoformat(),
                                 "duration_minutes": task.duration_minutes,
                                 "priority": task.priority, "frequency": task.frequency,
                                 "completed": task.completed} for task in pet.tasks]}
                     for pet in self.pets],
        }}

    def to_json(self) -> str:
        """Encode a portable, readable JSON backup without losing date/time types."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Owner":
        """Validate a versioned backup and reconstruct its Owner, Pet, and Task objects."""
        root = _record(data, {"schema_version", "owner"}, "backup")
        if type(root["schema_version"]) is not int or root["schema_version"] != 1:
            raise ValueError("Unsupported backup schema version.")
        info = _record(root["owner"], {"name", "available_minutes", "day_start", "day_end", "pets"}, "owner")
        _string_fields(info, ("name", "day_start", "day_end"))
        if not isinstance(info["pets"], list):
            raise ValueError("Pets must be a list.")
        pets = []
        for raw_pet in info["pets"]:
            pet = _record(raw_pet, {"id", "name", "species", "tasks"}, "pet")
            _string_fields(pet, ("id", "name", "species"))
            if not isinstance(pet["tasks"], list):
                raise ValueError("Tasks must be a list.")
            tasks = []
            for raw_task in pet["tasks"]:
                task = _record(raw_task, {"id", "series_id", "description", "scheduled_time", "due_date",
                                          "duration_minutes", "priority", "frequency", "completed"}, "task")
                _string_fields(task, ("id", "series_id", "description", "scheduled_time", "due_date",
                                      "priority", "frequency"))
                tasks.append(Task(**{**task, "due_date": date.fromisoformat(task["due_date"]),
                                     "scheduled_time": time.fromisoformat(task["scheduled_time"])}))
            pets.append(Pet(pet["name"], pet["species"], tasks, pet["id"]))
        return cls(info["name"], pets, info["available_minutes"],
                   time.fromisoformat(info["day_start"]), time.fromisoformat(info["day_end"]))

    @classmethod
    def from_json(cls, content: str | bytes) -> "Owner":
        """Parse a size-limited backup and reject invalid JSON or model values."""
        size = len(content.encode("utf-8")) if isinstance(content, str) else len(content)
        if size > MAX_JSON_BYTES:
            raise ValueError("Household backups must be at most 2 MB.")
        try:
            data = json.loads(content)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("The backup is not valid UTF-8 JSON.") from exc
        return cls.from_dict(data)

    def save_to_json(self, path: str | Path = "data.json") -> None:
        """Atomically save the household so a failed write preserves the previous file."""
        payload = self.to_json()
        if len(payload.encode("utf-8")) > MAX_JSON_BYTES:
            raise ValueError("Household backups must be at most 2 MB.")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                    prefix=f".{target.name}.", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                with suppress(OSError):
                    temporary.unlink(missing_ok=True)

    @classmethod
    def load_from_json(cls, path: str | Path = "data.json") -> "Owner":
        """Restore a complete household from a file created by save_to_json."""
        target = Path(path)
        if target.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("Household backups must be at most 2 MB.")
        return cls.from_json(target.read_bytes())


@dataclass
class DailyPlan:
    """Selected tasks and explicit reasons for excluded pending tasks."""

    on_date: date
    scheduled: list[tuple[Pet, Task]] = field(default_factory=list)
    skipped: list[tuple[Pet, Task, str]] = field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        """Total the remaining active care time used by the plan."""
        return sum(task.duration_minutes for _, task in self.scheduled)

    def to_rows(self) -> list[dict]:
        """Build readable UI and CSV rows with selection explanations."""
        return [{
            "Time": f"{task.scheduled_time:%H:%M}–{task.end_at():%H:%M}",
            "Pet": pet.name,
            "Task": task.description,
            "Minutes": task.duration_minutes,
            "Priority": task.priority,
            "Why": f"{task.priority.title()} priority; fits availability and remaining budget.",
        } for pet, task in self.scheduled]


@dataclass
class Scheduler:
    """Retrieve tasks through Owner and select a conflict-free plan across all pets."""

    owner: Owner

    def filter_tasks(self, *, pet_id: str | None = None, pet_name: str | None = None,
                     completed: bool | None = None, on_date: date | None = None) -> list[tuple[Pet, Task]]:
        """Filter all pets' tasks by stable pet ID/name, status, or due date."""
        return [(pet, task) for pet, task in self.owner.get_all_tasks()
                if (pet_id is None or pet.id == pet_id)
                and (pet_name is None or pet.name.casefold() == pet_name.casefold())
                and (completed is None or task.completed == completed)
                and (on_date is None or task.due_date == on_date)]

    def sort_by_time(self, tasks: list[tuple[Pet, Task]] | None = None) -> list[tuple[Pet, Task]]:
        """Return a chronological copy, preserving insertion order for exact ties."""
        source = self.owner.get_all_tasks() if tasks is None else tasks
        return sorted(source, key=lambda entry: (entry[1].due_date, entry[1].scheduled_time))

    @staticmethod
    def _overlap(first: Task, second: Task) -> bool:
        """Check full intervals, allowing adjacent tasks and rejecting different dates."""
        a, b = _minutes(first.scheduled_time), _minutes(second.scheduled_time)
        return (first.due_date == second.due_date
                and a < b + second.duration_minutes and b < a + first.duration_minutes)

    def detect_conflicts(self, on_date: date) -> list[tuple[Task, Task]]:
        """Report every overlapping pair of pending tasks across all pets."""
        tasks = [task for _, task in self.filter_tasks(on_date=on_date, completed=False)]
        return [(first, second) for i, first in enumerate(tasks) for second in tasks[i + 1:]
                if self._overlap(first, second)]

    def next_available_slot(self, on_date: date, duration_minutes: int,
                            earliest: time | None = None, exclude_task_id: str | None = None) -> time | None:
        """Find the first gap across all pending pet tasks within the owner's hours."""
        self.owner.validate()
        if type(duration_minutes) is not int or not 1 <= duration_minutes <= 1440:
            raise ValueError("Slot duration must be an integer from 1 to 1440 minutes.")
        candidate = max(_minutes(earliest or self.owner.day_start), _minutes(self.owner.day_start))
        limit = _minutes(self.owner.day_end)
        if candidate + duration_minutes > limit:
            return None
        for _, task in self.sort_by_time(self.filter_tasks(on_date=on_date, completed=False)):
            if task.id == exclude_task_id:
                continue
            start = _minutes(task.scheduled_time)
            end = start + task.duration_minutes
            if end <= candidate:
                continue
            if candidate + duration_minutes <= start:
                return time(candidate // 60, candidate % 60)
            candidate = max(candidate, end)
            if candidate + duration_minutes > limit:
                return None
        return time(candidate // 60, candidate % 60)

    def generate_schedule(self, on_date: date | None = None) -> DailyPlan:
        """Choose tasks by priority within fixed times, hours, and remaining care budget."""
        day = on_date or date.today()
        self.owner.validate()
        plan = DailyPlan(day)
        # Stable sorting keeps owner/pet insertion order for exact ties.
        candidates = sorted(self.filter_tasks(on_date=day, completed=False), key=lambda entry: (
            PRIORITIES.index(entry[1].priority), entry[1].scheduled_time, entry[1].duration_minutes))
        used = 0
        for pet, task in candidates:
            start = _minutes(task.scheduled_time)
            if start < _minutes(self.owner.day_start) or start + task.duration_minutes > _minutes(self.owner.day_end):
                reason = "Outside the owner's available hours."
            else:
                conflict = next(((other_pet, other) for other_pet, other in plan.scheduled
                                 if self._overlap(task, other)), None)
                if conflict:
                    other_pet, other = conflict
                    reason = f"Conflicts with {other_pet.name}: {other.description} ({other.priority} priority)."
                elif used + task.duration_minutes > self.owner.available_minutes:
                    reason = f"Exceeds the remaining {self.owner.available_minutes - used} minute care budget."
                else:
                    plan.scheduled.append((pet, task))
                    used += task.duration_minutes
                    continue
            plan.skipped.append((pet, task, reason))
        plan.scheduled = self.sort_by_time(plan.scheduled)
        plan.skipped.sort(key=lambda entry: entry[1].scheduled_time)
        return plan
