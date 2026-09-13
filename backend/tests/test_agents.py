"""Unit tests for the LangGraph stub (no LLM)."""

from uuid import uuid4

from app.agents.graph import run_stub

_STUB_MESSAGE = "Agent runtime is not implemented yet for this project."


def test_run_stub_returns_placeholder() -> None:
    project_id = uuid4()
    result = run_stub(project_id)
    assert result["project_id"] == str(project_id)
    assert result["message"] == _STUB_MESSAGE
