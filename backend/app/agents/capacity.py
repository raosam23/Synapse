from app.models.task import Task

POINTS_PER_PERSON_PER_SPRINT = 8


def sprint_capacity(member_count: int) -> int:
    return member_count * POINTS_PER_PERSON_PER_SPRINT


def select_tasks_for_capacity(tasks: list[Task], capacity: int) -> list[Task]:
    used = 0
    selected: list[Task] = []
    for task in tasks:
        if task.story_points is None:
            continue
        if used + task.story_points > capacity:
            continue
        selected.append(task)
        used += task.story_points
    return selected
