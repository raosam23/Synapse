from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.models.task import Task
from app.models.team_member import TeamMember
from app.schemas.agents import SprintPlan


def _client() -> ChatOpenAI:
    """Build a client for the OpenAI"""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.2,
    )


SYSTEM_PROMPT = """
You assign backlog tasks to team members for one spint.
- Use each member's skills. Prefer a close skill match.
- Only use member ids and task ids from human message. DO NOT INVENT IDS.
- Each task at most once. A member may get more than one task.
- Respect story points: do not load anyone beyond 8 points.
- Skip asks with no story_points.
- If nothing fits, return an empty assignments list.
"""


def plan_sprint(*, tasks: list[Task], members: list[TeamMember]) -> SprintPlan:
    """Plan a sprint by assigning tasks to team members.

    Args:
        tasks: List of tasks to assign.
        members: List of team members.

    Returns:
        SprintPlan: The planned sprint.
    """
    task_lines = "\n".join(
        f"- {task.id} | {task.story_points} pts | {task.title}" for task in tasks
    )

    member_lines = "\n".join(
        f"- {member.id} | skills: {', '.join(member.skills or [])}"
        for member in members
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                ("Tasks:\n{task_lines}\n\nMembers:\n{member_lines}\n\n"),
            ),
        ]
    )

    chain = prompt | _client().with_structured_output(SprintPlan)

    return chain.invoke(
        {
            "task_lines": task_lines,
            "member_lines": member_lines,
        }
    )
