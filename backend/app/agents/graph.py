from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.analyzer import analyze_requirements


class StubState(TypedDict):
    """State for the stub agent"""

    project_id: str
    requirements: str
    duration_weeks: int
    team_skills: list[str]
    opinion: str
    tasks: list[dict[str, Any]]


def analyze_requirements_node(state: StubState) -> StubState:
    result = analyze_requirements(
        requirements=state["requirements"],
        duration_weeks=state["duration_weeks"],
        team_skills=state["team_skills"],
    )
    return {
        "opinion": result.opinion,
        "tasks": [task.model_dump() for task in result.tasks],
    }


def _build_graph() -> CompiledStateGraph[StubState]:
    """Build the graph"""
    graph = StateGraph(StubState)
    graph.add_node("analyze_requirements_node", analyze_requirements_node)
    graph.add_edge(START, "analyze_requirements_node")
    graph.add_edge("analyze_requirements_node", END)
    return graph.compile()


compiled_graph = _build_graph()


def run_analyze_requirements(
    project_id: UUID,
    requirements: str,
    duration_weeks: int,
    team_skills: list[str],
) -> dict[str, Any]:
    return compiled_graph.invoke(
        {
            "project_id": str(project_id),
            "requirements": requirements,
            "duration_weeks": duration_weeks,
            "team_skills": team_skills,
            "opinion": "",
            "tasks": [],
        }
    )
