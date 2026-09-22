"""Unit tests for sprint capacity rules (no LLM, no DB)."""

from uuid import uuid4

from app.agents.capacity import select_tasks_for_capacity, sprint_capacity
from app.models.task import Task


def _task(points: int | None) -> Task:
    return Task(title="t", project_id=uuid4(), story_points=points)


def test_sprint_capacity_two_members() -> None:
    assert sprint_capacity(2) == 16


def test_select_skips_unestimated_tasks() -> None:
    a, b, c = _task(3), _task(None), _task(5)
    assert select_tasks_for_capacity([a, b, c], capacity=8) == [a, c]


def test_select_skips_task_that_does_not_fit_then_takes_a_later_one() -> None:
    a, b, c, d = _task(5), _task(5), _task(8), _task(3)
    assert select_tasks_for_capacity([a, b, c, d], capacity=16) == [a, b, d]


def test_select_rejects_task_larger_than_capacity() -> None:
    huge = _task(13)
    assert select_tasks_for_capacity([huge], capacity=8) == []
