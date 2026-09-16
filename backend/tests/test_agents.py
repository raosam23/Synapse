"""Unit tests for the LangGraph stub (no LLM)."""

from unittest.mock import patch
from uuid import uuid4

from app.agents.graph import run_analyze_requirements
from app.schemas.agents import BacklogTaskDraft, RequirementAnalysis


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
