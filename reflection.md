# PawPal+ — Project Reflection

**Student:** Harsha Priya Ganapathy  
**Course:** CodePath AI110 — Foundations of AI Engineering  
**Project:** Module 2 · PawPal+

## 1. System Design

### a. Initial design

I organized PawPal+ around three user actions: adding a pet, managing its care tasks, and viewing or completing a daily plan across the household.

The initial design assigned a distinct responsibility to each required class. `Owner` holds identifying information, pets, and preferences. `Pet` manages its tasks. `Task` represents a care activity. `Scheduler` organizes the tasks retrieved through `Owner.get_all_tasks()`. Python dataclasses keep the model's attributes explicit and reduce constructor boilerplate.

The owner-wide retrieval method is an important architectural boundary: adding a second pet automatically includes its tasks in sorting, filtering, conflict detection, and plan generation.

### b. Design changes

The first skeleton represented a routine with a start date and a set of completion dates. I replaced that approach when the complete requirements made new-instance recurrence explicit. The final Task represents one dated occurrence. Completion preserves that occurrence as history and creates a new pending task with a new ID and the same series ID.

I added `DailyPlan` to return selected tasks, excluded tasks, reasons, and care-time totals together. I also added JSON serialization to `Owner` so the same model can be restored after an application restart. The final UML includes both the persistence methods and the next-available-slot algorithm.

## 2. Scheduling Logic and Tradeoffs

### a. Constraints and priorities

The scheduler filters to pending tasks due on the selected date, considers high/medium/low priority, and breaks ties by time and duration. It only selects tasks that fit the owner's hours, remaining active-care budget, and non-overlap constraint. The result is displayed chronologically.

A separate gap-finding algorithm scans the shared calendar and returns the earliest free interval of a requested duration. It merges overlapping occupied time as it scans, considers every pet, and can exclude the occurrence currently being edited. It suggests a time without moving existing tasks.

### b. Tradeoffs

The priority scheduler uses a readable greedy algorithm. It gives predictable priorities and clear explanations but does not guarantee a globally optimal combination of tasks. One high-priority task may consume time that several lower-priority activities could otherwise use.

Conflict detection checks full intervals rather than only equal start times. Pairwise comparison is O(n²), which is reasonable for a small household and easier to inspect than a more complex event index. Gap finding sorts and scans intervals in O(n log n).

Recurring tasks advance from their due date when completed. This preserves history and prevents unbounded future-task generation, while keeping overdue care visible on its original date.

## 3. AI Collaboration

### a. How I used AI

I used ChatGPT Work for design scaffolding, multi-file implementation, test generation, UI integration, and documentation. The workflow connected the GitHub repository with actual Python execution so generated code could be evaluated through the CLI and tests.

I compared two context strategies using the same assistant: a broad implementation request with the initial partial attachment, and the complete assignment with explicit recurrence and acceptance requirements. The structured comparison in `ai_interactions.md` records the inputs, resulting designs, useful output, problems, evidence, and final decision.

The work remained in one continuous conversation, organized by design, backend, algorithms, UI, storage, and testing stages. This retained the relationships between requirements and implementation without claiming that separate model providers or chat sessions were used.

### b. Judgment and correctness evidence

I retained the suggested four-class separation and owner-wide retrieval method. I modified the completion-date-set idea because it did not demonstrate a newly created Task. The final tests assert different IDs, the next due date, pending status, preserved series identity, and no duplicate next occurrence after repeated completion.

I also distinguished CSV plan export from durable household persistence. A schedule export alone cannot restore all pets, task identities, or history. The final JSON implementation serializes the whole model, validates restored data, and atomically replaces the saved file only after a successful write.

## 4. Testing and Verification

### a. What I tested

The suite has **107 passing cases** covering core models, sorting and filtering, cross-pet retrieval and conflicts, recurrence, priority and budget constraints, availability boundaries, empty states, invalid inputs, identity-safe edits, next-available-slot search, persistence, the CLI, and the Streamlit interface.

Persistence tests reconstruct the complete household, preserve completion and recurrence IDs, reject malformed schemas and values, and simulate failed disk operations to confirm the previous file survives. A CLI integration test saves and loads in separate processes. A Streamlit test opens a fresh application session and restores the saved household.

The tests measure **100% statement coverage for `pawpal_system.py`** and **98% combined backend/CLI statement coverage**. UI behavior is exercised through Streamlit's `AppTest`; those percentages describe backend/CLI statements rather than UI line coverage.

### b. Confidence

My confidence level is **4/5 stars** for the defined single-household workflow. The test suite covers normal behavior and meaningful failure cases. Additional work would be needed for authenticated multi-user hosting, concurrent editing, time zones, overnight availability, and large household datasets.

## 5. Reflection

### a. What went well

The clearest result is the separation between the model and the interface. The same backend powers the CLI, the interactive plan, JSON restoration, and the test suite. Explicit reasons for excluded tasks make the scheduling algorithm understandable, while unique IDs protect task management when descriptions repeat.

The persistence extension also reinforces the value of a clear data model: dates, times, completion history, and recurrence identity can be reconstructed consistently rather than stored as display-only rows.

### b. What I would improve

A future iteration could add a bulk recurrence-series editor, a calendar view, and a more advanced optimizer. A hosted multi-user version would need authentication and storage isolated by household. Concurrent writes would need coordination beyond the current single-household atomic file replacement.

### c. Key takeaway

A diagram, implementation, and tests should explain the same system. Context engineering improved the AI output most when requirements were translated into specific observable behavior. Working as the lead architect meant preserving a simple model, refining suggestions when the requirements demanded it, and using execution evidence to support the final design.
