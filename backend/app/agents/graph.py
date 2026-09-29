from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.analyzer import analyze_requirements
from app.agents.planner import plan_sprint
from app.agents.risk import analyze_risk
from app.models import Comment, Task, TeamMember


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


class PlanState(TypedDict):
    """State for the plan sprint agent"""

    tasks: list[Task]
    members: list[TeamMember]
    assignments: list[dict[str, Any]]


def plan_sprint_node(state: PlanState) -> PlanState:
    """Plan a sprint by assigning tasks to team members"""
    assignments = plan_sprint(tasks=state["tasks"], members=state["members"])
    return {
        "assignments": [
            assignment.model_dump() for assignment in assignments.assignments
        ]
    }


def _build_plan_sprint_graph() -> CompiledStateGraph[PlanState]:
    """Build the graph for the plan sprint agent"""
    graph = StateGraph(PlanState)
    graph.add_node("plan_sprint_node", plan_sprint_node)
    graph.add_edge(START, "plan_sprint_node")
    graph.add_edge("plan_sprint_node", END)
    return graph.compile()


compiled_plan_sprint_graph = _build_plan_sprint_graph()


def run_plan_sprint(tasks: list[Task], members: list[TeamMember]) -> dict[str, Any]:
    """Run the plan sprint agent.

    Args:
        tasks: List of tasks to assign.
        members: List of team members.

    Returns:
        dict[str, Any]: The assignments.
    """
    return compiled_plan_sprint_graph.invoke(
        {
            "tasks": tasks,
            "members": members,
            "assignments": [],
        }
    )


class RiskState(TypedDict):
    """State for the risk analyzer agent"""

    tasks: list[Task]
    comments: list[Comment]
    flags: list[dict[str, Any]]


def analyze_risk_node(state: RiskState) -> RiskState:
    result = analyze_risk(tasks=state["tasks"], comments=state["comments"])
    return {"flags": [flag.model_dump() for flag in result.flags]}


def _build_analyze_risk_graph() -> CompiledStateGraph[RiskState]:
    """Build the graph for the risk analyzer agent"""

    graph = StateGraph(RiskState)
    graph.add_node("analyze_risk_node", analyze_risk_node)
    graph.add_edge(START, "analyze_risk_node")
    graph.add_edge("analyze_risk_node", END)
    return graph.compile()


compiled_analyze_risk_graph = _build_analyze_risk_graph()


def run_analyze_risks(tasks: list[Task], comments: list[Comment]) -> dict[str, Any]:
    return compiled_analyze_risk_graph.invoke(
        {
            "tasks": tasks,
            "comments": comments,
            "flags": [],
        }
    )
