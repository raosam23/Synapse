"""Requirement Analyzer agent: opinion + backlog task drafts for any pasted product requirements."""

from __future__ import annotations

import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.schemas.agents import RequirementAnalysis

SYSTEM_PROMPT = """\
You are a tech lead turning pasted product requirements into GitHub feature tickets \
plus a short opinion about the product.

MATCH THE PRODUCT
The paste may describe any kind of work (web, mobile, data, hardware, research, ops). \
Ticket the user's actual product. Do not assume a web app, API, auth scheme, or scrum board. \
Do not invent capabilities that are not in the paste (e.g. Slack, Gantt, CI/CD, file upload, \
realtime) unless the paste asks for them.

TICKET SPLIT
- Exactly one concern per ticket. Never join two features with "and" in the title.
- No two tickets may cover the same feature, and no ticket may cover two features. \
  Before you finish, check every pair of tickets for overlap and fix it.
- Do not assign people or fill sprint capacity. Duration is how long the team has, \
  not a feature — only mention sprints/boards if the paste asks for them.

EACH TICKET
- title: "[Feature]: <name the gap>" (not a generic label like "Setup").
- description: markdown with exactly these H2 headers in order:
    ## Description — 3–6 short paragraphs: the hole, why it matters, this slice, \
what this ticket must not do (sibling tickets stay out of scope), and what it depends on
    ## Required behavior — 5+ bullets unique to this ticket. If a bullet could be \
pasted onto a sibling ticket unchanged, delete it. Only mention APIs, UI, or status \
codes if this slice and the paste actually need them.
    ## Acceptance criteria — 3+ checkboxes, including tests for this slice where they apply.
    ## Out of scope — list the sibling ticket titles
    ## Related requirement
    ## Sequence
- story_points — your estimate, or omit if you cannot judge it.

OPINION
Feasibility, main risks, suggested build order for the *product*. Never write about \
the tickets, the outline, or your own process.
"""

_FEATURE_PREFIX = re.compile(r"^\[feature\]:\s*", re.IGNORECASE)


def _client() -> ChatOpenAI:
    """Build a ChatOpenAI client from app settings.
    Returns:
        ChatOpenAI: Client using LLM_MODEL and OPENAI_API_KEY from env.
    """
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.2,
    )


def feature_title(title: str) -> str:
    """Ensure a GitHub-style [Feature]: prefix.
    Args:
        title: Raw ticket title from the model.
    Returns:
        str: Title starting with [Feature]:.
    """
    stripped = title.strip()
    rest = _FEATURE_PREFIX.sub("", stripped).strip() or stripped
    return f"[Feature]: {rest}"


def analyze_requirements(
    *,
    requirements: str,
    duration_weeks: int,
    team_skills: list[str] | None = None,
) -> RequirementAnalysis:
    """Analyze pasted requirements into an opinion and backlog drafts.
    Args:
        requirements: The pasted project requirements.
        duration_weeks: The project duration in weeks.
        team_skills: Flattened skills from the project roster, if any.
    Returns:
        RequirementAnalysis: Opinion text and backlog task drafts.
    """
    skills = ", ".join(team_skills) if team_skills else "unknown"
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                (
                    "Project duration: {duration_weeks} weeks\n"
                    "Team skills: {skills}\n"
                    "Requirements:\n{requirements}"
                ),
            ),
        ]
    )
    chain = prompt | _client().with_structured_output(RequirementAnalysis)
    result = chain.invoke(
        {
            "duration_weeks": duration_weeks,
            "skills": skills,
            "requirements": requirements,
        }
    )
    return result.model_copy(
        update={
            "tasks": [
                t.model_copy(update={"title": feature_title(t.title)})
                for t in result.tasks
            ]
        }
    )
