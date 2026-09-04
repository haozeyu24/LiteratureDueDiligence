# Workflow Control Artifacts

This folder stores run-level control state.

- `01_state/`: canonical SQLite workflow database.
- `02_snapshots/`: exported JSON snapshots for audit and handoff.

Treat the SQLite database as canonical. Snapshot files are derived exports and
may lag until the relevant workflow step regenerates them.
