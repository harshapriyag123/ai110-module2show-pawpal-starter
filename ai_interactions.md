# PawPal+ — AI Collaboration Record

## Agent Workflow

### Task requested

Implement the CodePath AI110 PawPal+ project in `harshapriyag123/ai110-module2show-pawpal-starter`, including the four-class OOP design, a CLI-first demo, multi-pet scheduling algorithms, tests, a Streamlit interface, and submission documentation. The final rubric added explicit evidence for all five bonus categories.

### Tool and working method

ChatGPT Work served as the AI coding assistant, with the connected GitHub plugin for repository changes and local Python execution for the CLI and tests. The work proceeded through design, backend implementation, UI integration, algorithm extensions, persistence, and documentation within one continuous conversation.

### Files created or modified

| Files | Work performed |
|---|---|
| `pawpal_system.py` | Dataclass models, owner-wide retrieval, sorting/filtering, interval conflicts, recurrence, priority/budget selection, next-available-slot search, and JSON save/load. |
| `main.py` | Two-pet CLI demo, conflict/priority/free-slot output, and `--save` / `--load` arguments. |
| `app.py` | Model-backed forms, session state, automatic disk persistence, JSON backup/restore, free-slot suggestions, status feedback, and explained plans. |
| `diagrams/uml_draft.mmd` | Initial four-class design checkpoint. |
| `diagrams/uml_final.mmd`, `diagrams/uml.mmd` | Final classes, attributes, methods, and relationships, including storage and gap finding. |
| `tests/test_pawpal.py` | Core model and scheduling behavior. |
| `tests/test_available_slot.py` | Gap finding across pets, overlap unions, adjacency, exclusions, and invalid durations. |
| `tests/test_persistence.py` | Full-household round trips, schema validation, saved history, failed-write protection, and size limits. |
| `tests/test_app.py`, `tests/test_cli.py`, `tests/conftest.py` | UI persistence across sessions, CLI persistence across processes, integration behavior, and isolated test files. |
| `README.md`, `reflection.md`, `ai_interactions.md` | System manual, rubric evidence, design reflection, and this collaboration/comparison record. |
| `.github/workflows/tests.yml`, `requirements.txt`, `pyproject.toml` | Dependency and automated test configuration. |
| `.streamlit/config.toml`, `.gitignore` | App styling and exclusions for runtime household/coverage/temp files. |

### What the agent completed

- Created and preserved a UML-to-skeleton design checkpoint.
- Implemented the backend and ran the standalone demo before integrating Streamlit.
- Made the scheduler retrieve all pets' tasks through `Owner.get_all_tasks()`.
- Added recurrence that creates and stores a new dated Task instance.
- Added a next-available-slot algorithm that searches the shared pending calendar without moving existing tasks.
- Implemented full-household JSON persistence with atomic replacement and validated restoration.
- Ran the behavioral and integration suite: **107 passing tests**; `pawpal_system.py` statement coverage is **100%**.
- Recorded actual demo output and test results in the project documentation.

### Corrections and engineering judgment

No separate student edits outside this AI-assisted session are recorded. Corrections made during the workflow included replacing the initial completion-date-set design with explicit task instances, updating deprecated Streamlit width arguments, separating a household backup from a CSV plan export, isolating persistence paths in tests, and preserving an unreadable saved file rather than silently overwriting it.

## Prompt Comparison

### Task and comparison method

The comparison concerns the **same recurring-task design problem** at two stages of this project's development. Both strategies used ChatGPT Work; the changed variable was the amount and structure of requirements context. The initial and final code checkpoints provide the output evidence. This is a comparison of prompting/context strategies, not a claim that different model providers were benchmarked.

| Comparison field | Strategy A — broad request with partial context | Strategy B — complete requirements with explicit behavior and tests |
|---|---|---|
| **Model / tool used** | ChatGPT Work with the GitHub plugin. | The same ChatGPT Work assistant and GitHub plugin. |
| **Prompt / task** | User request: “i need to implement this,” with the first Markdown attachment. Its detailed Phases 3–6 content was absent. The task was to scaffold the four classes for a pet-care planner. | The subsequent full course-text attachment specified: completing a daily/weekly task must automatically create a new instance; Scheduler must read the owner's combined tasks; tests must cover recurrence, sorting, and conflicts. The supplied grading rubric later made all evidence requirements explicit. |
| **Response / output** | The initial Task skeleton used `start_date` and `completed_dates`, representing one routine with completion history. It also established dataclasses, the four core classes, and `Owner.get_all_tasks()`. | The implementation changed Task to one dated occurrence with `due_date`, `completed`, `id`, and `series_id`. `Task.mark_complete()` returns a new pending instance; `Pet.mark_task_complete()` attaches it and avoids duplicates. |
| **Useful output** | Quickly established clear responsibilities and the owner-to-pets-to-tasks relationships. The shared owner retrieval boundary was retained. | Converted the assignment's wording into observable behavior: a different object ID, the correct next due date, pending status, preserved series identity, and visibility through the owner. |
| **Problems with output** | A single routine plus a set of completion dates would not demonstrate the required new-instance recurrence. The initial skeleton also left behavior unimplemented, so its diagram alone was insufficient evidence. | More context produced a larger implementation and test surface. The design needed a clear orchestration method so callers would store the new occurrence, and idempotence tests so repeated completion would not duplicate it. |
| **Evaluation evidence** | [Initial class skeleton commit](https://github.com/harshapriyag123/ai110-module2show-pawpal-starter/commit/cd32fe47c4c444386beefff7dfbff7572b4b0031) and `diagrams/uml_draft.mmd`. | `test_completion_creates_distinct_next_occurrence`, `test_undo_and_recomplete_does_not_duplicate_future_task`, `test_generated_occurrence_is_visible_to_owner_scheduler`, and the dated recurrence line in `main.py` output. |
| **Final student decision** | Retain the simple four-class OOP structure and the owner-wide retrieval method. Replace the routine-level completion-set representation. | Adopt the complete-context, behavior-driven strategy for the final project. Use dated task instances, a pet-level completion method, and automated acceptance checks to keep the implementation aligned with the requirements. |

### Conclusion

The strongest strategy was to supply the complete assignment, identify observable acceptance behavior, and evaluate the generated design against executable tests. Broad prompts were useful for scaffolding; explicit requirements and test expectations resolved the important modeling decision. The final implementation retains the useful OOP structure from Strategy A and the occurrence-based recurrence behavior from Strategy B.
