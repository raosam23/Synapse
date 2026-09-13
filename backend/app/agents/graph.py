from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph


class StubState(TypedDict):
    """State for the stub agent"""

    project_id: str
    message: str


def stub(state: StubState) -> StubState:
    """Stub agent"""
    return {
        "project_id": state["project_id"],
        "message": "Agent runtime is not implemented yet for this project.",
    }


def _build_graph() -> CompiledStateGraph[StubState]:
    """Build the graph"""
    graph = StateGraph(StubState)
    graph.add_node("stub", stub)
    graph.add_edge(START, "stub")
    graph.add_edge("stub", END)
    return graph.compile()


compiled_graph = _build_graph()


def run_stub(project_id: UUID) -> dict[str, Any]:
    return compiled_graph.invoke({"project_id": str(project_id), "message": ""})
