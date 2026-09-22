from app.models.task import Task

POINTS_PER_PERSON_PER_SPRINT = 8


def sprint_capacity(member_count: int) -> int:
    return member_count * POINTS_PER_PERSON_PER_SPRINT


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
