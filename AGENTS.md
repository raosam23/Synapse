# AGENTS.md

Shared instructions for any AI coding tool working in this repository (Cursor, Claude Code, Codex, Copilot, and similar). Keep changes aligned with this file and with MVP scope in GitHub issue #4.

How the development will happen?
The development will be done by the Human.
This is a learning project, you should not write any code on your own, DO NOT CHANGE ANYTHING WITHOUT MY PERMISSION
As I want to learn, I expect to iteratively learn, you will check the requirement, and then check what I have done, and then tell me what I should do File by File or even smaller.
Start small and iteratively develop the app to production level.
There is no deadline for this
You tell me what to do for a file/unit, give me hints, I will tell you if I understand what to do or not, and refine your hints or help me write that specific piece.
If I don't understand at all, and if I give up at some point, I will tell you to make changes yourself, there you have full freedom to work on that file
if I say fix it, do it yourself, do it for me, then you should do the changes yourself, otherwise keep giving me hints
For terminal commands and setup steps, give me the commands to run, do not run them yourself unless I explicitly ask you to.
You have full access to the entire codebase, both frontend and backend, please do not ask me to share the code, or ask me progress on any file/folder. You are free to scan the entire codebase for you analysis
Help me write the code, that's it.

## What is Synapse

Synapse is an AI-powered project management app. Users paste requirements as plain text; agents turn that into structured tasks, assign work across a team, and flag delivery risk — then the team manages work on a Kanban board.

It is not a generic chatbot. The product is the agent loop plus the board: plan work, surface risk, and keep tasks moving.

## Repository layout

```
Synapse/
├── backend/          # FastAPI + LangGraph (Python)
├── frontend/         # Next.js app
├── .github/          # Issue templates, workflows
├── AGENTS.md         # This file
└── README.md
```

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, LangGraph, Python 3.12+ |
| Frontend | Next.js, React |
| Database | Postgres (planned; not wired yet) |
| Package managers | `uv` (backend), `bun` (frontend) |

## MVP scope (v1)

Source of truth: GitHub issue **#4**.

**In scope**

- Agents: Requirement Analyzer, Sprint Planner, Risk Analyzer
- Kanban board (drag and drop, task cards, risk flags)
- Inputs: plain-text requirements; team members (name + optional skills); optional deadline
- Manual task reassignment

**Deferred to v2**

- Timeline Generator, Standup Generator
- Gantt chart, file upload (PDF/txt), auth/multi-tenant, realtime collab, Slack/email

**Out of scope for v1**

- Do not build deferred/out-of-scope features unless an issue explicitly expands scope

## Local development

### Backend

```bash
cd backend
uv sync
uv run uvicorn main:app --reload
```

Health check: `GET /health` → `{"status":"ok"}`

### Frontend

```bash
cd frontend
bun install
bun run dev
```

## Git and PR workflow

- Branch from `main`; one issue per PR
- Name branches like `chore/14-agents-md` or `feature/<issue>-short-slug`
- PR description must include `Closes #<issue-number>`
- Do not push straight to `main`
- Never commit secrets (`.env`, tokens, API keys). `.env` is gitignored

## Code review

- Cursor Bugbot (`cursor[bot]` / `Cursor Bugbot` check) reviews PRs on this repo
- Prefer small, reviewable PRs over large mixed changes

## Working with agents

- Prefer editing existing files over creating new ones when possible
- Match existing style; do not add drive-by refactors unrelated to the ticket
- Ask before expanding MVP scope beyond #4
- When unsure, check open issues and #4 before inventing product behavior
