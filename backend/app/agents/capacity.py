from datetime import UTC, date, datetime

from app.models.task import Task

POINTS_PER_PERSON_PER_SPRINT = 8


def sprint_capacity(member_count: int) -> int:
    """Calculate the capacity of a sprint for a team."""
    return member_count * POINTS_PER_PERSON_PER_SPRINT


def days_left_in_sprint(end_date: date, today: date | None = None) -> int:
    """Inclusive days remaining in a sprint (0 if the window has ended)."""
    if today is None:
        today = datetime.now(UTC).date()
    return max(0, (end_date - today).days + 1)


def pull_into_current_sprint(days_left: int) -> bool:
    """Pull into the current sprint when at least half of a 2-week window remains."""
    return days_left >= 7


def select_tasks_for_capacity(
    tasks: list[Task],
    capacity: int,
    *,
    max_task_points: int | None = None,
) -> list[Task]:
    """Pick backlog tasks that fit a team point budget.

    Args:
        tasks: Candidate backlog tasks in priority order.
        capacity: Total leftover points for the team this sprint.
        max_task_points: Largest single-task size anyone can still take
            (typically max remaining per person). Tasks above this are
            skipped so they do not consume team budget no one can use.
    """
    used = 0
    selected: list[Task] = []
    for task in tasks:
        if task.story_points is None:
            continue
        if max_task_points is not None and task.story_points > max_task_points:
            continue
        if used + task.story_points > capacity:
            continue
        selected.append(task)
        used += task.story_points
    return selected
