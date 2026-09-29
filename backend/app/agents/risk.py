from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.models.comment import Comment
from app.models.task import Task
from app.schemas.agents import RiskAnalysis


def _client() -> ChatOpenAI:
    """Build a client for the OpenAI"""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.2,
    )


SYSTEM_PROMPT = """
You flag delivery risk on existing tasks.
- Use only task ids from the human message. DO NOT INVENT IDS.
- Set risk_flag to true if the task looks likely to slip (large points, unclear work, blocker in comments, overloaded assignee, etc.)
- Set risk_flag to false if it looks on track.
- Return one flag per task. If you have nothing to say, still include every given task with false.
"""


def analyze_risk(*, tasks: list[Task], comments: list[Comment]) -> RiskAnalysis:
    """Analyze the risk for a list of tasks.

    Args:
        tasks: List of tasks to analyze.
        comments: Comments on those tasks (may be empty).

    Returns:
        RiskAnalysis: The risk analysis for the tasks.
    """
    task_lines = "\n".join(
        f"- {task.id} | {task.story_points} pts | {task.status} | {task.title}"
        for task in tasks
    )
    comment_lines = (
        "\n".join(
            f"- {comment.task_id} | {'ai' if comment.is_ai else 'human'} | {comment.body}"
            for comment in comments
        )
        or "(none)"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                "Tasks:\n{task_lines}\n\nComments:\n{comment_lines}\n\n",
            ),
        ]
    )
    client = _client()

    chain = prompt | client.with_structured_output(RiskAnalysis)
    return chain.invoke(
        {
            "task_lines": task_lines,
            "comment_lines": comment_lines,
        }
    )
