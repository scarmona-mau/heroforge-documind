# Plan: Task Manager with CSV Persistence

## Context

The project has no task management system. The user wants a standalone to-do item tracker (title, status, priority, due date, notes) that persists to a CSV file and automatically displays pending tasks when a Claude Code session starts. This gives developers a lightweight, always-visible work-tracking layer that surfaces at every session open without any manual steps.

---

## Files to Create / Modify

| Action | Path |
|--------|------|
| **Modify** | `src/documind/config.py` |
| **Create** | `src/documind/task_manager.py` |
| **Create** | `tests/unit/task_manager/__init__.py` |
| **Create** | `tests/unit/task_manager/test_task_manager.py` |
| **Modify** | `.claude/hooks/ValidateEnvironment.sh` |

---

## 1. `src/documind/config.py` — Add `TASKS_FILE`

Append one line to the "Application Settings" block (after `OUTPUT_DIR`):

```python
TASKS_FILE = get_env("TASKS_FILE", "tasks.csv")   # root-relative by default
```

---

## 2. `src/documind/task_manager.py` — New module

### CSV Schema (column order matters for `csv.DictReader`)

```
id, title, status, priority, created_at, updated_at, due_date, notes
```

- `id`: UUID v4 string
- `status`: `pending | in_progress | completed`
- `priority`: `low | medium | high`
- `created_at` / `updated_at`: `datetime.utcnow().isoformat()`
- `due_date`: `YYYY-MM-DD` or `""` when absent
- `notes`: free text; newlines serialised as the literal `\n` to keep single-row-per-task

### `Task` dataclass

```python
@dataclass
class Task:
    id: str
    title: str
    status: str        # pending | in_progress | completed
    priority: str      # low | medium | high
    created_at: str
    updated_at: str
    due_date: str = ""
    notes: str = ""
```

### `TaskManager` class — key method signatures

```python
class TaskManager:
    def __init__(self, tasks_file: str = TASKS_FILE) -> None: ...

    def load_tasks(self) -> List[Task]:
        # Returns [] when file absent; skips rows with invalid status/priority

    def save_tasks(self, tasks: List[Task]) -> None:
        # Atomic write: write to tasks.csv.tmp, then os.replace() to tasks.csv

    def add_task(self, title: str, priority: str = "medium",
                 due_date: str = "", notes: str = "") -> Dict[str, Any]:
        # status defaults to "pending"; raises ValueError on invalid priority
        # Returns dataclasses.asdict(new_task)

    def update_task_status(self, task_id: str, new_status: str) -> Dict[str, Any]:
        # Accepts full UUID or 8-char prefix; raises KeyError if not found,
        # ValueError on invalid status; updates updated_at

    def list_tasks(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        # Sorted: in_progress → pending → completed, then created_at asc
        # Raises ValueError on invalid status_filter

    def display_startup_summary(self) -> None:
        # Prints open-tasks block to stdout; never raises (errors swallowed)
```

### `display_startup_summary()` output format

```
--------------------------------------------------
 OPEN TASKS  (2 in progress, 3 pending)
--------------------------------------------------
 [IN PROGRESS]  Implement RAG pipeline            [HIGH]   due 2026-05-16
 [PENDING]      Update requirements.txt           [LOW]    due 2026-05-20
--------------------------------------------------
```

When no open tasks: `OPEN TASKS  — none pending`
When file missing: `OPEN TASKS  — no tasks file found (tasks.csv)`

Title is left-padded to 45 chars. Due date shown only when set. Completed tasks are never shown.

### `__main__` entry point (bottom of file)

```python
if __name__ == "__main__":
    TaskManager().display_startup_summary()
```

---

## 3. `.claude/hooks/ValidateEnvironment.sh` — Append task display

Add after the final `echo "✅ Environment validation complete..."` line:

```bash
# Show pending tasks
echo ""
if command -v python3 &> /dev/null; then
    python3 -m src.documind.task_manager 2>/dev/null || true
fi
```

The `2>/dev/null || true` ensures import errors or missing `.env` never block session startup.
`python3 -m src.documind.task_manager` works because the `package.json` check at the top of the script guarantees we're in the project root, which Python adds to `sys.path` automatically for `-m` invocations.

---

## 4. Tests — `tests/unit/task_manager/test_task_manager.py`

Follows existing pattern: class-based (`TestTaskManager`), real file I/O via `tempfile.mkdtemp()`, no mocking.

**Key fixtures:**
- `temp_dir` → `tempfile.mkdtemp()` with `shutil.rmtree` teardown
- `tasks_file` → path string inside `temp_dir`
- `manager` → `TaskManager(tasks_file=tasks_file)`
- `manager_with_tasks` → manager pre-populated with 3 tasks of varied priority

**Test cases to cover:**

- `load_tasks` — returns `[]` when file missing; round-trip preserves all fields; skips corrupted rows
- `save_tasks` — creates CSV with correct headers; atomic write (`.tmp` → rename)
- `add_task` — creates pending task with UUID; sets both timestamps; stores optional fields; raises on invalid priority; persists to CSV immediately
- `update_task_status` — changes status + updates `updated_at`; accepts 8-char prefix; raises `KeyError` on unknown id; raises `ValueError` on invalid status
- `list_tasks` — filters by status; correct sort order; returns dicts (not dataclasses); raises on invalid filter
- `display_startup_summary` — use `capsys`; shows header block; shows in-progress and pending; omits completed; no-op when no open tasks; no-op when file absent; never raises

---

## Verification

```bash
# 1. Unit tests
pytest tests/unit/task_manager/ -v

# 2. Full test suite — confirm no regressions
pytest tests/ -v

# 3. Manual smoke test
python3 -m src.documind.task_manager              # "no tasks file found"

python3 -c "
from src.documind.task_manager import TaskManager
m = TaskManager('tasks.csv')
m.add_task('Test task', priority='high', due_date='2026-05-20')
m.add_task('Another task', priority='low')
m.display_startup_summary()
"

# 4. Hook integration — trigger a session restart or run the hook directly
bash .claude/hooks/ValidateEnvironment.sh
# Expected: existing validation output + OPEN TASKS block at the bottom

# 5. Cleanup test file
rm -f tasks.csv
```
