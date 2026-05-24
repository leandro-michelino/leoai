from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable
import traceback
import uuid


@dataclass
class Job:
    job_id: str
    kind: str
    status: str
    created_at: str
    updated_at: str
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None


class JobQueue:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = Lock()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(self, kind: str, payload: dict[str, Any]) -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            kind=kind,
            status="queued",
            created_at=self._now(),
            updated_at=self._now(),
            payload=payload,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def set_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.updated_at = self._now()

    def set_done(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "done"
            job.result = result
            job.updated_at = self._now()

    def set_failed(self, job_id: str, exc: Exception) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            job.result = {"traceback": traceback.format_exc(limit=8)}
            job.updated_at = self._now()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 100) -> list[Job]:
        with self._lock:
            items = list(self._jobs.values())
        items.sort(key=lambda j: j.created_at, reverse=True)
        return items[:limit]

    def run_guarded(self, job_id: str, fn: Callable[[], dict[str, Any]]) -> None:
        self.set_running(job_id)
        try:
            result = fn()
            self.set_done(job_id, result)
        except Exception as exc:  # noqa: BLE001
            self.set_failed(job_id, exc)
