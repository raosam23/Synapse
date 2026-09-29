"""Unit tests for the LangGraph agents (no LLM)."""

from unittest.mock import patch
from uuid import uuid4

from app.agents.graph import (
    run_analyze_requirements,
    run_analyze_risks,
    run_plan_sprint,
)
from app.models.comment import Comment
from app.models.task import Task
from app.models.team_member import TeamMember
from app.schemas.agents import (
    BacklogTaskDraft,
    RequirementAnalysis,
    RiskAnalysis,
    SprintAssignment,
    SprintPlan,
    TaskRiskFlag,
)


def test_run_analyze_requirements_returns_opinion_and_tasks() -> None:
    fake = RequirementAnalysis(
        opinion="Looks feasible",
        tasks=[
            BacklogTaskDraft(
                title="[Feature]: Example task",
                description="*" * 700,
                story_points=3,
            )
        ],
    )
    project_id = uuid4()
    with patch("app.agents.graph.analyze_requirements", return_value=fake):
        result = run_analyze_requirements(
            project_id,
            "build a thing",
            4,
            ["Python", "React", "PostgreSQL"],
        )

        assert result["project_id"] == str(project_id)
        assert len(result["tasks"]) == len(fake.tasks)
        assert result["tasks"][0]["title"] == fake.tasks[0].title


def test_run_plan_sprint_returns_assignments() -> None:
    task = Task(
        title="[Feature]: Example",
        project_id=uuid4(),
        story_points=3,
    )
    member = TeamMember(
        skills=["Python"],
        user_id=uuid4(),
        project_id=task.project_id,
    )
    fake = SprintPlan(
        assignments=[
            SprintAssignment(task_id=task.id, member_id=member.id),
        ]
    )

    with patch("app.agents.graph.plan_sprint", return_value=fake):
        result = run_plan_sprint([task], [member])

    assert len(result["assignments"]) == 1
    assert result["assignments"][0]["task_id"] == task.id
    assert result["assignments"][0]["member_id"] == member.id


def test_run_analyze_risks_returns_flags() -> None:
    task = Task(
        title="[Feature]: Risky",
        project_id=uuid4(),
        story_points=8,
    )
    comment = Comment(task_id=task.id, body="Blocked on API access.")
    fake = RiskAnalysis(
        flags=[TaskRiskFlag(task_id=task.id, risk_flag=True)],
    )

    with patch("app.agents.graph.analyze_risk", return_value=fake):
        result = run_analyze_risks([task], [comment])

    assert len(result["flags"]) == 1
    assert result["flags"][0]["task_id"] == task.id
    assert result["flags"][0]["risk_flag"] is True
