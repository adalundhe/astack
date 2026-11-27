"""Separated offline oracle for `rule-no-implicit-states`."""
from __future__ import annotations

from pathlib import Path

FIXED_SRC = '''from __future__ import annotations

from enum import Enum


class JobState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class JobEvent(Enum):
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    COMPLETE = "complete"
    FAIL = "fail"
    RETRY = "retry"


class InvalidTransitionError(ValueError):
    """Raised when an event is not permitted from the current job state."""


_TRANSITIONS: dict[tuple[JobState, JobEvent], JobState] = {
    (JobState.PENDING, JobEvent.START): JobState.RUNNING,
    (JobState.RUNNING, JobEvent.PAUSE): JobState.PAUSED,
    (JobState.PAUSED, JobEvent.RESUME): JobState.RUNNING,
    (JobState.RUNNING, JobEvent.COMPLETE): JobState.COMPLETED,
    (JobState.RUNNING, JobEvent.FAIL): JobState.FAILED,
    (JobState.PAUSED, JobEvent.FAIL): JobState.FAILED,
    (JobState.FAILED, JobEvent.RETRY): JobState.RUNNING,
}


class JobProcessor:
    """Explicit state machine for job lifecycle transitions."""

    def __init__(self) -> None:
        self._state: JobState = JobState.PENDING
        self.result: str | None = None
        self.error: str | None = None

    @property
    def state(self) -> JobState:
        return self._state

    def transition(self, event: JobEvent, *, payload: str | None = None) -> JobState:
        next_state = _TRANSITIONS.get((self._state, event))
        if next_state is None:
            raise InvalidTransitionError(
                f"cannot apply {event.value!r} while in state {self._state.value!r}"
            )

        if next_state is JobState.COMPLETED:
            self.result = payload
            self.error = None
        elif next_state is JobState.FAILED:
            self.error = payload
            self.result = None
        elif next_state is JobState.RUNNING:
            self.error = None
            self.result = None

        self._state = next_state
        return self._state

    def start(self) -> None:
        self.transition(JobEvent.START)

    def pause(self) -> None:
        self.transition(JobEvent.PAUSE)

    def resume(self) -> None:
        self.transition(JobEvent.RESUME)

    def complete(self, result: str) -> None:
        self.transition(JobEvent.COMPLETE, payload=result)

    def fail(self, error: str) -> None:
        self.transition(JobEvent.FAIL, payload=error)

    def retry(self) -> None:
        self.transition(JobEvent.RETRY)
'''

FIXED_TESTS = '''import unittest

from src.job_processor import InvalidTransitionError, JobProcessor, JobState


class JobProcessorBasicTest(unittest.TestCase):
    def test_start_and_complete_stores_result(self):
        job = JobProcessor()
        self.assertEqual(job.state, JobState.PENDING)
        job.start()
        self.assertEqual(job.state, JobState.RUNNING)
        job.complete("artifact-123")
        self.assertEqual(job.state, JobState.COMPLETED)
        self.assertEqual(job.result, "artifact-123")
        self.assertIsNone(job.error)

    def test_start_and_fail_stores_error(self):
        job = JobProcessor()
        job.start()
        job.fail("upstream timeout")
        self.assertEqual(job.state, JobState.FAILED)
        self.assertEqual(job.error, "upstream timeout")
        self.assertIsNone(job.result)

    def test_pause_resume_and_retry_paths(self):
        job = JobProcessor()
        job.start()
        job.pause()
        self.assertEqual(job.state, JobState.PAUSED)
        job.resume()
        self.assertEqual(job.state, JobState.RUNNING)
        job.fail("transient error")
        self.assertEqual(job.state, JobState.FAILED)
        job.retry()
        self.assertEqual(job.state, JobState.RUNNING)
        self.assertIsNone(job.error)
        job.complete("ok")
        self.assertEqual(job.state, JobState.COMPLETED)
        self.assertEqual(job.result, "ok")

    def test_illegal_transitions_raise_and_preserve_state(self):
        pending = JobProcessor()
        for fn in (pending.pause, pending.resume, lambda: pending.complete("x"), lambda: pending.fail("e"), pending.retry):
            with self.assertRaises(InvalidTransitionError):
                fn()
            self.assertEqual(pending.state, JobState.PENDING)

        done = JobProcessor()
        done.start()
        done.complete("final")
        for fn in (done.start, done.pause, done.resume, lambda: done.complete("other"), lambda: done.fail("err"), done.retry):
            with self.assertRaises(ValueError):
                fn()
            self.assertEqual(done.state, JobState.COMPLETED)
            self.assertEqual(done.result, "final")
            self.assertIsNone(done.error)

        paused = JobProcessor()
        paused.start()
        paused.pause()
        with self.assertRaises(ValueError):
            paused.complete("cannot-finish-paused")
        self.assertEqual(paused.state, JobState.PAUSED)
        paused.fail("aborted")
        self.assertEqual(paused.state, JobState.FAILED)
        with self.assertRaises(ValueError):
            paused.complete("cannot-complete-failed")
        self.assertEqual(paused.state, JobState.FAILED)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "job_processor.py").write_text(FIXED_SRC, encoding="utf-8")
    (repo / "tests" / "test_job_processor.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Replaced the four overlapping boolean flags in src/job_processor.py with an explicit "
            "JobState Enum and centralized transition table in JobProcessor.transition, rejecting "
            "all illegal transitions with InvalidTransitionError (a ValueError subclass) without "
            "mutating state, and added tests for valid paths and rejected transitions."
        ),
    }
