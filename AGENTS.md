# AGENTS.md

Shared instructions for any AI coding tool working in this repository (Cursor, Claude Code, Codex, Copilot, and similar). Keep changes aligned with this file. Product behavior for **v1.0.0** is defined here (supersedes older notes in GitHub issue #4 where they conflict).

How the development will happen?
The development will be done by the Human.
This is a learning project, you should not write any code on your own, DO NOT CHANGE ANYTHING WITHOUT MY PERMISSION
As I want to learn, I expect to iteratively learn, you will check the requirement, and then check what I have done, and then tell me what I should do File by File or even smaller.
Start small and iteratively develop the app to production level.
There is no deadline for this
You tell me what to do for a file/unit, give me hints, I will tell you if I understand what to do or not, and refine your hints or help me write that specific piece.
If I don't understand at all, and if I give up at some point, I will tell you to make changes yourself, there you have full freedom to work on that file
if I say fix it, do it yourself, do it for me, then you should do the changes yourself, otherwise keep giving me hints
YOU SHOULD NOT MAKE ANY CHANGES UNLESS AND UNTIL I SAY SO — this applies to everything, not just terminal commands: editing/writing any file (code, docs, config, migrations, AGENTS.md itself), running any command that mutates the database/filesystem/git history (`alembic upgrade`, `git commit`, `git push`, etc.), and anything else that changes the state of this repo or its infrastructure. Default to giving me hints, explanations, and commands to run myself. Read-only/inspection actions (reading files, `git status`, `git diff`, `git log`, checking CI status, etc.) are fine for you to do on your own. Only make a change directly yourself when I explicitly say so (e.g. "fix it", "do it for me", "do it yourself").
For terminal commands and setup steps specifically: give me the commands to run, do not run them yourself unless I explicitly ask you to.
You have full access to the entire codebase, both frontend and backend, please do not ask me to share the code, or ask me progress on any file/folder. You are free to scan the entire codebase for you analysis
Help me write the code, that's it.

## What is Synapse

Synapse is an AI-powered scrum / project management app. A user creates a **project**, pastes **requirements** (including team, duration, and project details), and the AI:

1. Reviews the requirements and shares an **opinion / analysis**
2. Breaks work into tickets
3. Plans **fixed 2-week sprints** for the whole project (v1.0.0: sprint length is always 2 weeks — not dynamically computed)
4. Assigns a smart subset of work into the current sprint by capacity (story points)
5. Keeps pulling from the backlog as people finish work, until the project is done

It is not a generic chatbot. The product is the **agent loop + backlog + sprint board + comments**.

### End-to-end flow (v1.0.0)

1. **Project created** — user pastes requirements text that includes team size / members, project duration, and project details.
2. **AI reviews** — agents analyze the requirements and produce an opinion (feasibility, risks, high-level plan).
3. **Sprints defined** — project timeline is divided into consecutive **2-week sprints** (constant for v1).
4. **Tickets created** — AI creates tasks; new tasks start in **`backlog`** (not on the sprint board).
5. **Initial sprint fill** — AI assigns only what fits capacity (typically ~1–2 tasks per person based on complexity / story points). Remaining work stays in backlog.
6. **Execution** — assignees move work `todo` → `doing` → `done` on the board (manual drag-and-drop and/or AI).
7. **Pull next work** — when someone finishes (or has spare capacity), AI may pull another backlog item into the **current** sprint or schedule it for the **next** sprint, based on remaining effort and time left in the sprint.
8. **Repeat** until the project is complete.

### Task lifecycle (status)

Tasks use exactly four statuses (store all four in the DB; do not invent extra ones without updating this file and the schema):

| Status | Meaning | On sprint Kanban board? |
|--------|---------|-------------------------|
| `backlog` | Created, not yet pulled into an active sprint | **No** |
| `todo` | In the current sprint, ready to start (after assignment into the sprint) | Yes |
| `doing` | Actively in progress | Yes |
| `done` | Finished | Yes |

**Board rule:** the sprint Kanban shows only `todo` / `doing` / `done`. `backlog` lives in a separate backlog view, never as a board column.

**Default for new tasks:** `backlog`. Moving into a sprint + assignment → `todo`.

### Comments = progress signal (no CI/CD yet)

v1.0.0 does **not** integrate with GitHub, Jenkins, or other CI/CD to detect commits or pipeline success.

Status / sprint decisions that need “what happened in the real world” use **comments** (word of mouth):

- Any **logged-in** user can comment on a task
- The **AI** may also post comments when useful (e.g. why it reassigned or pulled a ticket)
- Agents read comment history to update status, pull next backlog items, or adjust the sprint board

### Agents (v1.0.0)

- **Requirement Analyzer** — parse requirements, opinion/analysis, create backlog tasks + estimates
- **Sprint Planner** — fill sprints by capacity (story points), assign to team members, pull next work when capacity frees up
- **Risk Analyzer** — flag delivery risk on tasks / plan

### Authentication (v1.0.0)

`User` and `TeamMember` are **not the same thing**:

- **`User`** — a login identity (`email` + `password_hash`). Created via `/api/v1/auth/register`. Required to authenticate and to comment/act as a real person.
- **`TeamMember`** — a roster **seat on a project** (`name` + `skills` + `project_id`). Linked to an existing `User` via `user_id`. The same `User` may sit on more than one project; the same `User` cannot be added twice to the **same** project (unique `(project_id, user_id)`). A Synapse account is required before roster or assignment ([#50](https://github.com/raosam23/Synapse/issues/50), [#56](https://github.com/raosam23/Synapse/issues/56)).

Auth is JWT in an httpOnly `access_token` cookie (not an `Authorization` header):

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`
- Register and login set the cookie (`httponly`, `samesite=lax`) and return the user JSON only — the JWT is not in the response body
- All `projects`, `team-members`, `tasks`, `task-dependencies`, and `GET /auth/me` endpoints require a valid `access_token` cookie
- A task's `created_by_id` is always set server-side from the authenticated user — never accepted from the client
- Creating a `TeamMember` requires an existing `User` and an existing `Project` (`project_id`); assigning a task to an unlinked `TeamMember` is rejected (`409`); the assignee must belong to the **same** project as the task (`409` if they do not)
- `POST /api/v1/auth/logout` revokes the token's `jti` (`RevokedToken` blocklist) and clears the cookie. A revoked JWT is rejected even if the cookie is still present.

## Repository layout

```
Synapse/
├── backend/           # FastAPI + LangGraph (Python)
├── frontend/          # Next.js app
├── .github/           # Issue templates, workflows
├── docker-compose.yml # Postgres + app services
├── .env.example       # Local DB env template
├── AGENTS.md          # This file
└── README.md
```

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, LangGraph, Python 3.12+ |
| Frontend | Next.js, React |
| Database | Postgres (Docker Compose + SQLModel/Alembic) |
| Package managers | `uv` (backend), `bun` (frontend) |

## MVP scope (v1.0.0)

Source of truth: **this file** (and open GitHub issues for implementation slices). Issue #4 remains historical context.

**In scope**

- Project creation with pasted requirements (team, duration, details)
- AI opinion / analysis on requirements
- Fixed **2-week** sprints for the project duration
- Backlog + sprint Kanban (`todo` / `doing` / `done`)
- AI task creation, capacity-based assignment, and pull-from-backlog loop
- Story-point (or equivalent effort) estimates and per-person sprint capacity
- Risk flags on tasks
- Task comments (humans + AI); agents use comments as the progress signal
- Manual reassignment / board moves by users
- Minimal auth so “logged-in” comment authors exist

**Deferred to v2+**

- Dynamic sprint length (AI-chosen weeks)
- GitHub / Jenkins / CI/CD–driven status updates
- Gantt chart, file upload (PDF/txt), multi-tenant, realtime collab, Slack/email
- Standalone Timeline / Standup generator products (standup-style updates may appear as comments in v1)

**Out of scope for v1**

- Do not build deferred features unless an issue explicitly expands scope

## Planned schema (v1.0.0) — for implementers

Keep models minimal; add only what the flow above needs.

| Entity | Purpose (high level) |
|--------|----------------------|
| `User` | Logged-in identity for auth, comments / authorship (`email` + `password_hash`) |
| `Project` | Name, requirements text, duration, AI opinion/analysis, fixed sprint length (2 weeks), project status |
| `TeamMember` | Belongs to a project (`project_id`); name + skills; `user_id` link to an existing `User`; unique per `(project_id, user_id)` |
| `Sprint` | Belongs to a project; ordered 2-week window (`start_date` / `end_date`) |
| `Task` | Belongs to a project (`project_id`); `status`; optional `assignee_id` (same project); optional `sprint_id` (null while backlog); story points / effort; risk flag; `created_by_id` |
| `TaskDependency` | Optional `from_task` → `to_task` edges |
| `Comment` | Belongs to a task; body; author (user and/or AI); timestamps |

**Schema progress:** `User`, `Project`, `TeamMember`, `Task`, and `TaskDependency` are migrated. `TeamMember` and `Task` have required `project_id`. Roster uniqueness is `(project_id, user_id)`, not global `user_id`. Add `Sprint` and `Comment` in follow-up tickets. `Task.sprint_id` is still a loose UUID (real FK in the Sprint ticket).

## Local development

Human-facing detail: [`README.md`](./README.md). Critical commands below must stay in sync with the README.

### Env + Postgres

```bash
cp .env.example .env
docker compose up database -d
```

`.env` is gitignored. Host apps use `DATABASE_URL` with `postgresql+asyncpg://…@localhost:5432/…` (see `.env.example`). Compose backend uses hostname `database` instead of `localhost`.

### Backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/health` → `{"status":"ok"}`

Migrations are not applied on container start. After changing models under `backend/app/models/`:

```bash
uv run alembic revision --autogenerate -m "short description"
uv run alembic upgrade head
```

### Frontend

```bash
cd frontend
bun install
bun run dev
```

### Full stack via Compose

```bash
docker compose up --build
# then migrate (host or exec):
cd backend && uv run alembic upgrade head
# or: docker compose exec backend uv run alembic upgrade head
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
- Ask before expanding beyond **v1.0.0** scope in this file
- When unsure about product behavior, follow this file first, then open issues
