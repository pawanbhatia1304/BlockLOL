"""
ForensiVault Backend — Async Job Manager
Tracks background jobs (wipe, file-erase, carve) with unique IDs,
state transitions, and cancellation support.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from backend.models.schemas import JobState, JobStatus, JobType
from backend.ws.manager import manager as ws_manager

logger = logging.getLogger("forensivault.jobs")


class Job:
    """Internal representation of a running or completed job."""

    def __init__(self, job_type: JobType) -> None:
        self.job_id: str = f"{job_type.value[:2].upper()}-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:8]}"
        self.job_type = job_type
        self.state = JobState.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self.progress_percent: float = 0.0
        self.message: str = ""
        self.result: dict[str, Any] | None = None
        self._task: asyncio.Task | None = None
        self._cancel_event = asyncio.Event()

    # ── helpers ──────────────────────────────────────────────

    def is_cancel_requested(self) -> bool:
        return self._cancel_event.is_set()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    def to_status(self) -> JobStatus:
        return JobStatus(
            job_id=self.job_id,
            job_type=self.job_type,
            state=self.state,
            created_at=self.created_at,
            updated_at=self.updated_at,
            progress_percent=self.progress_percent,
            message=self.message,
            result=self.result,
        )


# ─── Manager Singleton ──────────────────────────────────────────

class JobManager:
    """
    Central registry for all background jobs.

    Usage:
        job = job_manager.create(JobType.WIPE)
        await job_manager.run(job, my_async_worker, args...)
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    # ── CRUD ─────────────────────────────────────────────────

    def create(self, job_type: JobType) -> Job:
        job = Job(job_type)
        self._jobs[job.job_id] = job
        logger.info("Job created: %s (%s)", job.job_id, job_type.value)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list_all(self) -> list[JobStatus]:
        return [j.to_status() for j in self._jobs.values()]

    # ── execution ────────────────────────────────────────────

    async def run(
        self,
        job: Job,
        worker: Callable[..., Coroutine],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Launch *worker(job, *args, **kwargs)* as a background task.
        The worker must accept ``job`` as its first argument and should:
          • update job.state, job.progress_percent, job.message
          • call ``await self.report_progress(job, {...})`` periodically
          • check ``job.is_cancel_requested()`` and stop gracefully
        """
        async def _wrapped() -> None:
            try:
                job.state = JobState.RUNNING
                job.updated_at = datetime.now(timezone.utc)
                await self.report_progress(job)
                await worker(job, *args, **kwargs)
                if job.state == JobState.RUNNING:
                    job.state = JobState.COMPLETED
                    job.progress_percent = 100.0
            except asyncio.CancelledError:
                job.state = JobState.CANCELLED
                job.message = "Job cancelled by user"
            except Exception as exc:
                job.state = JobState.FAILED
                job.message = str(exc)
                logger.exception("Job %s failed", job.job_id)
            finally:
                job.updated_at = datetime.now(timezone.utc)
                await self.report_progress(job)

        job._task = asyncio.create_task(_wrapped())

    async def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job or job.state != JobState.RUNNING:
            return False
        job.request_cancel()
        if job._task:
            job._task.cancel()
        return True

    # ── progress broadcasting ────────────────────────────────

    async def report_progress(self, job: Job, extra: dict[str, Any] | None = None) -> None:
        data: dict[str, Any] = {
            "state": job.state.value,
            "progress_percent": round(job.progress_percent, 2),
            "message": job.message,
        }
        if extra:
            data.update(extra)
        if job.result:
            data["result"] = job.result
        await ws_manager.broadcast_progress(
            event="job_progress",
            job_id=job.job_id,
            data=data,
        )


job_manager = JobManager()
