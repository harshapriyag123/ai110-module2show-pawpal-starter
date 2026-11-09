# PawPal+ Project Reflection

> AI-assisted technical reflection draft. The implementation and verification statements describe this repository and this ChatGPT Work session. Personal learning and opinions should be reviewed and personalized by the student before submission; this document does not claim unobserved manual work or separate chat sessions.

## 1. System Design

### a. Initial design

Three core user actions are:

1. Add a pet to an owner's household.
2. Create and manage a dated care task for a pet, such as feeding, walking, or a reminder.
3. View a sorted daily plan across all pets, resolve conflicts, and complete tasks.

The initial UML separated four responsibilities: `Owner` stores pets and preferences; `Pet` stores its care tasks; `Task` stores one activity's data; and `Scheduler` organizes the owner's combined task collection. Dataclasses keep the data model explicit and avoid repetitive constructors. `Owner.get_all_tasks()` is the single retrieval path used by the scheduler, so a second pet is included automatically.

### b. Design changes

The first skeleton considered a routine with a start date and a set of completion dates. After the full assignment text was supplied, that design was changed to **one Task per dated occurrence**, because the requirement explicitly asks for a new instance after daily or weekly completion. A `series_id` connects related occurrences while unique task IDs preserve individual history. `Pet.mark_task_complete()` attaches the returned next instance and prevents duplicates on repeated completion.

A small `DailyPlan` dataclass was added to return selected tasks and reasons for skipped tasks together. This keeps display formatting out of the selection algorithm and lets the CLI and Streamlit share the same result. The final UML documents these changes.

## 2. Scheduling Logic and Tradeoffs

### a. Constraints and priorities

The scheduler filters pending tasks by selected due date, then considers high, medium, and low priority. Ties use start time, then duration, with stable insertion order for exact ties. A task must fit wholly within the owner's available hours, fit the remaining active-care budget, and avoid overlaps with already selected tasks. Selected tasks are finally displayed chronologically.

The budget represents remaining work rather than total work already completed. Fixed task times are preserved. Any excluded task receives an availability, conflict, or budget reason so the owner can make the next decision.

### b. Tradeoffs

The greedy priority algorithm is easy to explain but is not guaranteed to maximize the number of tasks or produce a globally optimal plan. One long high-priority task can displace several lower-priority tasks. This is reasonable for an introductory project where predictable priorities and readable logic matter.

Conflict detection checks complete time intervals rather than only equal start times. Its pairwise O(n²) approach is simple to inspect and adequate for a small household, although a sweep-line algorithm would scale better. Conflicts are flagged and lower-ranked tasks excluded; the system does not silently change care times.

Recurrence stores completed history and creates just one next instance. This meets the new-instance requirement without generating an unbounded calendar. It also means an overdue routine must be completed or edited rather than silently advancing itself.

## 3. AI Collaboration

### a. How AI was used

The user supplied the GitHub repository and course instructions and asked ChatGPT Work to implement them. The assistant inspected the starter, drafted UML and class skeletons, implemented the CLI-first backend, added behavioral tests, wired the UI, and prepared documentation. Automatic edits across multiple files and executable tests were the most useful capabilities: recurrence affects `Task`, `Pet`, the UI, the demo, and the tests together.

Providing the complete assignment text was especially useful context engineering. The initial Markdown omitted the detailed later phases; the second text attachment made the sorting, filtering, new-instance recurrence, and verification requirements explicit.

This work used **one continuous conversation**, not separate chats for each phase. Design, backend, UI, testing, and documentation were handled as separate work stages. Separate phase-specific chats could be helpful in future work, but they were not used here and are not claimed.

### b. Judgment and verification

An early date-rule-only recurrence design was modified after comparison with the complete instructions: a new pending Task is now created and attached to the pet. This was a requirements-driven change to an AI-proposed design, not a claim that the student manually rejected code in an IDE.

Verification uses tests that assert a different task ID, the next due date, preserved series identity, pending status, and no duplicate occurrence after repeated completion. A separate test confirms the scheduler calls the owner's shared retrieval method. These checks provide evidence beyond plausible-looking generated code.

The student should still review the code, explain these choices in their own words, and perform their own acceptance walkthrough before submitting the personal reflection.

## 4. Testing and Verification

### a. What was tested

The suite contains 68 tests: model completion/addition and validation, daily/weekly recurrence, chronological sorting, pet/status/date filtering, retrieval across pets, exact-time and interval conflicts, adjacency, priority and care-budget selection, availability boundaries, empty and zero-budget cases, editing/deleting by ID, and the CLI demo.

Eight Streamlit `AppTest` scenarios additionally exercise forms, session state, adding multiple pets, invalid input, task editing, generated plans, completion/recurrence, deletion, filters, and preference updates. They verify actual UI actions reach the backend rather than testing only mocked button handlers.

Local verification passed all tests. The measured coverage is 100% of `pawpal_system.py` statements and 99% combined for the backend and CLI. This is not a claim of complete UI coverage or proof of correctness for every possible input.

### b. Confidence

Technical confidence is **4/5 stars** for the documented single-owner, same-day workflow. The tests check meaningful constraints and recurrence edge dates, including year and leap-day boundaries. Future tests should cover a larger generated dataset, concurrent sessions, persistent storage failures, time zones, and overnight availability if those features are introduced.

## 5. Reflection

### a. What went well

The strongest result is the clean boundary between the model and the UI: the same scheduler powers a readable CLI and the Streamlit plan. Explicit skipped-task explanations make the algorithm's choices visible, and stable identifiers keep duplicate descriptions from breaking edits or completion.

### b. What could improve

A next iteration could add JSON save/load, a series editor, and a user-controlled suggestion for the next free time slot. Durable storage would need validation and backup tests. A more advanced optimizer could improve budget usage, but its behavior should remain explainable.

### c. Key takeaway

A UML diagram, implementation, and verification suite should describe the same system. Acting as a lead architect means checking generated code against the requirements, choosing readable tradeoffs, and asking for evidence that the resulting behavior works. AI can accelerate implementation; a passing test suite and an honest account of the process make the work reviewable.
