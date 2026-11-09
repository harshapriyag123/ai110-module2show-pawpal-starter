# AI Interactions Log

## Agent Workflow

**Task supplied:** The user linked `harshapriyag123/ai110-module2show-pawpal-starter`, said “i need to implement this,” and attached the CodePath PawPal+ project instructions. A later attachment supplied the complete Phases 3–6 requirements.

**Tool used:** ChatGPT Work with the connected GitHub plugin, local Python execution, pytest and Streamlit AppTest. A browser visual check was attempted, but the browser could not reach this execution environment's local server.

**Work completed by the assistant:**

- Inspected the starter repository and both instruction attachments.
- Drafted four-class UML and dataclass skeletons, preserving the design checkpoint in a separate commit.
- Implemented `pawpal_system.py` and the two-pet CLI `main.py` before integrating the UI.
- Added sorting, filtering, multi-pet interval conflicts, daily/weekly next-task creation, priority-based selection, availability, and care budgets.
- Connected `app.py` to the models using `st.session_state`, added editing/completion/filtering, explained results, and CSV export.
- Added backend, CLI, and UI tests, a CI workflow, final UML, README, and this reflection draft.
- Removed the tracked Python bytecode artifact from the final source tree and ignored generated coverage data.

**Corrections and review during the session:**

- Changed the initial completion-date-set design to explicit new Task instances when the complete course requirements became available.
- Replaced deprecated Streamlit width arguments after executing the UI against the installed version.
- Tested recurrence idempotence and owner-wide task retrieval instead of assuming those requirements were satisfied.

No student manual code corrections or separate phase-specific chat sessions were observed. The personal reflection is an AI-assisted draft for the student to review. No multi-model prompt comparison was performed or claimed.

## Extensions represented

- Priority-first scheduling within time and availability constraints.
- Structured CLI output, status indicators, metrics, conflict warnings, and explanatory tables.
- Multi-step agent workflow documented above.

Durable JSON persistence and a multi-model comparison are outside this implementation.
