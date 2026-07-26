"""
Async task management for prediction requests with progress tracking.

Each prediction runs in a background thread, updating a shared
progress dict that the frontend polls via GET /api/predict/task/{id}.
"""

import threading
import uuid
import time
from typing import Optional
from backend.models import PredictResponse

_tasks: dict[str, dict] = {}


def create_task(symbol: str) -> str:
    """Create a new task and return its ID."""
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "symbol": symbol,
        "stage": "Initializing",
        "progress": 0,
        "done": False,
        "error": None,
        "result": None,
    }
    return task_id


def update_progress(task_id: str, stage: str, progress: int) -> None:
    """Update the progress of a running task."""
    if task_id in _tasks:
        _tasks[task_id]["stage"] = stage
        _tasks[task_id]["progress"] = min(progress, 100)


def set_result(task_id: str, result: PredictResponse) -> None:
    """Mark a task as complete with its result."""
    if task_id in _tasks:
        _tasks[task_id]["stage"] = "Analysis Complete"
        _tasks[task_id]["progress"] = 100
        _tasks[task_id]["done"] = True
        _tasks[task_id]["result"] = result
        _tasks[task_id]["_completed_at"] = time.time()


def set_error(task_id: str, error: str) -> None:
    """Mark a task as failed with an error message."""
    if task_id in _tasks:
        _tasks[task_id]["stage"] = "Error"
        _tasks[task_id]["done"] = True
        _tasks[task_id]["error"] = error
        _tasks[task_id]["_completed_at"] = time.time()


def get_status(task_id: str) -> Optional[dict]:
    """Get the current status of a task."""
    return _tasks.get(task_id)


def cleanup_old_tasks(max_age_seconds: int = 3600) -> None:
    """Remove completed tasks older than max_age_seconds."""
    import time
    now = time.time()
    to_remove = []
    for tid, task in _tasks.items():
        if task.get("done") and task.get("_completed_at", 0) < now - max_age_seconds:
            to_remove.append(tid)
    for tid in to_remove:
        _tasks.pop(tid, None)
