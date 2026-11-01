# Synapse

[![CI](https://img.shields.io/github/actions/workflow/status/raosam23/Synapse/ci.yml.png?branch=main&label=CI)](https://github.com/raosam23/Synapse/actions/workflows/ci.yml) ![Status: in progress](https://img.shields.io/badge/status-in_progress-blue.png)

Synapse is an AI-assisted scrum app. A user creates a project from pasted requirements, and the API reviews those requirements, creates backlog tasks, lays out fixed 2-week sprints, and fills the current sprint by story-point capacity. Product rules for v1.0.0 are in [`AGENTS.md`](./AGENTS.md).

The backend below is implemented and covered by tests. The Next.js app can register, log in, create projects, manage the roster, generate sprints, list the backlog, move sprint work across `todo`, `doing`, and `done`, and call the three agent endpoints. A comments UI is not in the frontend yet.

---

## Backend

### Stack

| Piece | What the repo uses |
| --- | --- |
| API | FastAPI, Pydantic v2, Uvicorn |
| Data | SQLModel, SQLAlchemy async (`asyncpg`), Alembic (`psycopg`) |
| Auth | JWT (`python-jose`) in an httpOnly cookie, passwords hashed with bcrypt |
| Agents | LangGraph, `langchain-openai` (`ChatOpenAI`) |
| Database | Postgres 15.4 |
| Language | Python 3.12+ (`uv`) |
| Checks | pytest, pytest-asyncio, Ruff |

Settings load from the repo-root `.env` via `pydantic-settings` (`backend/app/core/config.py`). `LLM_MODEL` defaults to `gpt-4o`. Live agent calls need `OPENAI_API_KEY`. Tests mock the model, so pytest does not.

### Architecture

```text
HTTP
  └─ app/main.py                  FastAPI app, CORS for http://localhost:3000
       ├─ GET /health
       └─ app/api/router.py       prefix /api/v1
            └─ app/api/routes/     auth, projects, team members, sprints,
                                   tasks, task dependencies, comments
                 ├─ app/schemas/   request and response models
                 ├─ app/models/    SQLModel tables
                 ├─ app/db/        async session
                 └─ app/agents/    called from the project agent routes
                      ├─ llm.py        shared ChatOpenAI client
                      ├─ graph.py      one compiled LangGraph per agent
                      ├─ analyzer.py   requirements → opinion + backlog tasks
                      ├─ planner.py    skill-based assignment
                      ├─ capacity.py   8 points per person; 7-day sprint cutoff
                      └─ risk.py       risk_flag from tasks and comments
```

Each agent graph is a single node: `START` → that node → `END`. Capacity math stays in Python (`capacity.py` and the plan-sprint route). The planner model proposes assignees; the route enforces the 8-point cap.

Cookie auth is `get_current_user` in `app/core/security.py`. Logout writes the token `jti` to `revoked_tokens`. `created_by_id` on tasks, and `user_id` / `is_ai` on comments, are set on the server.

Tables: `users`, `revoked_tokens`, `projects`, `team_members`, `sprints`, `tasks`, `task_dependencies`, `comments`. `team_members` is unique on `(project_id, user_id)`. Display name is `User.name`, or `User.email` when name is null. New tasks default to `backlog` with `sprint_id` null. Task status is one of `backlog`, `todo`, `doing`, `done`.

### API

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs).

`GET /health` returns `{"status":"ok"}` and does not require a cookie. `POST /api/v1/auth/register` and `POST /api/v1/auth/login` are public and set the `access_token` cookie. Every other `/api/v1` route requires that cookie.

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | 201, sets cookie, returns the user |
| POST | `/api/v1/auth/login` | 200, sets cookie, returns the user |
| POST | `/api/v1/auth/logout` | Revokes the JWT and clears the cookie |
| GET | `/api/v1/auth/me` | Current user |

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v1/projects/` | Owner is the logged-in user |
| GET | `/api/v1/projects/` | Projects created by the current user |
| GET | `/api/v1/projects/{project_id}` | 404 for another user's project |
| PUT | `/api/v1/projects/{project_id}` | |
| DELETE | `/api/v1/projects/{project_id}` | 409 while it still has tasks, members, or sprints |
| POST | `/api/v1/projects/{project_id}/agents/run` | Requirement Analyzer. Second run is 409 |
| POST | `/api/v1/projects/{project_id}/agents/plan-sprint` | Sprint Planner |
| POST | `/api/v1/projects/{project_id}/agents/analyze-risk` | Risk Analyzer. 409 when the project has no tasks |

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v1/team-members/` | Existing `User` and `Project`. Duplicate `(project_id, user_id)` is 409 |
| GET | `/api/v1/team-members/` | Optional `?project_id=` |
| GET | `/api/v1/team-members/{team_member_id}` | |
| PUT | `/api/v1/team-members/{team_member_id}` | |
| DELETE | `/api/v1/team-members/{team_member_id}` | 409 if a task is still assigned to them |

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v1/sprints/` | Body: `project_id`, `start_date`. Creates consecutive 2-week windows from `duration_weeks` |
| GET | `/api/v1/sprints/` | Optional `?project_id=` |
| GET | `/api/v1/sprints/{sprint_id}` | |
| DELETE | `/api/v1/sprints/{sprint_id}` | 409 if tasks still point at it |

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v1/tasks/` | `created_by_id` comes from the cookie. Default status `backlog` |
| GET | `/api/v1/tasks/` | Optional `?project_id=` and `?status=` |
| GET | `/api/v1/tasks/{task_id}` | |
| PUT | `/api/v1/tasks/{task_id}` | Assignee and sprint must belong to the same project |
| DELETE | `/api/v1/tasks/{task_id}` | |

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v1/task-dependencies/` | `from_task` → `to_task`. Self-links rejected |
| GET | `/api/v1/task-dependencies/` | Optional `?from_task_id=` and `?to_task_id=` |
| GET | `/api/v1/task-dependencies/{task_dependency_id}` | |
| DELETE | `/api/v1/task-dependencies/{task_dependency_id}` | |

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v1/comments/` | `user_id` and `is_ai` are set on the server |
| GET | `/api/v1/comments/` | Optional `?task_id=` |
| GET | `/api/v1/comments/{comment_id}` | |
| PUT | `/api/v1/comments/{comment_id}` | |
| DELETE | `/api/v1/comments/{comment_id}` | |

**Requirement Analyzer** (`agents/run`). Reads the project requirements, duration, and roster skills. Writes `Project.ai_opinion` and inserts tasks as `backlog` with `sprint_id` null. A project that already has `ai_opinion` returns 409.

**Sprint Planner** (`agents/plan-sprint`). Needs a prior analysis, roster members linked to users, backlog tasks, and existing sprints (409 otherwise). Capacity is 8 story points per person per sprint. If 7 or more days remain in the first sprint, including `end_date`, work is pulled into that sprint; otherwise into the next sprint by `index`. Pulled tasks get `sprint_id`, status `todo`, and `assignee_id`.

**Risk Analyzer** (`agents/analyze-risk`). Reads the project's tasks and their comments, then sets `Task.risk_flag`. Task ids the model returns that are not on the project are skipped.

### Tests

From `backend/`, with Postgres up and `TEST_DATABASE_URL` pointing at `synapse_test` (see `.env.example`):

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Pytest migrates `synapse_test` and truncates that database only. It does not use `synapse_db`, which is what local uvicorn uses. Agent tests replace the LLM client, so they run without `OPENAI_API_KEY`.

---

## Frontend

Next.js 16, React 19, TypeScript, Tailwind CSS 4, Zustand, Bun.

| Route | What it does |
| --- | --- |
| `/` | Session check, links to login, register, or projects |
| `/login`, `/register` | Cookie auth against the API |
| `/projects`, `/projects/new` | List and create projects |
| `/projects/[id]` | Roster, sprint list, backlog, sprint board (`todo` / `doing` / `done`), and buttons for analysis, sprint planning, risk, and sprint creation |

There is no frontend test script. CI runs `bun run lint` and then prints `frontend tests TBD`.

The browser calls the API with credentials. Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (already in `.env.example`). The API allows `http://localhost:3000` with credentials.

---

## Run locally

Needs Docker Compose v2, [uv](https://docs.astral.sh/uv/), and [Bun](https://bun.sh/).

```bash
cp .env.example .env
docker compose up database -d
```

Postgres listens on `localhost:5432`. A new volume also creates `synapse_test`. If this volume was created before that init script existed:

```bash
docker compose exec database psql -U "$POSTGRES_USER" -c "CREATE DATABASE synapse_test;"
```

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

API: [http://localhost:8000](http://localhost:8000). `DATABASE_URL` must use `postgresql+asyncpg://`. Alembic rewrites that URL to `psycopg` for migrations.

```bash
cd frontend
bun install
bun run dev
```

UI: [http://localhost:3000](http://localhost:3000).

### Compose (API and UI in containers)

```bash
cp .env.example .env
docker compose up --build
```

The backend container uses hostname `database` in `DATABASE_URL`. Migrations do not run on container start:

```bash
cd backend && uv run alembic upgrade head
# or
docker compose exec backend uv run alembic upgrade head
```

### Alembic

From `backend/`:

```bash
uv run alembic current
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic history
```

After editing models in `backend/app/models/`:

```bash
uv run alembic revision --autogenerate -m "short description"
uv run alembic upgrade head
```

Review the generated script before committing it.

### Calling the API

Register and login put the JWT in an httpOnly `access_token` cookie (`samesite=lax`). The token is only in that cookie. Expiry is `ACCESS_TOKEN_EXPIRE_MINUTES` (30 in `.env.example`).

```bash
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@example.com", "password": "supersecret123", "name": "Dev"}'

curl -b cookies.txt http://localhost:8000/api/v1/auth/me

curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/v1/auth/logout
```

In Swagger, call register or login in the browser first. Later requests on the same origin send the cookie. This API does not read an `Authorization` header.

---

## CI

[`.github/workflows/ci.yml`](./.github/workflows/ci.yml) runs on pull requests and pushes to `main`:

1. **lint** — Ruff on the backend, ESLint on the frontend (`bun install --frozen-lockfile`).
2. **test** — Postgres 15.4 service database `synapse_ci`, then `alembic upgrade head` and `uv run pytest`. The workflow sets `DATABASE_URL` itself. Local pytest uses `TEST_DATABASE_URL` instead, and does not use `synapse_ci`.
3. **docker** — builds `synapse-backend:ci` and `synapse-frontend:ci`. Images are not pushed.

---

## Layout

```text
Synapse/
├── backend/            # FastAPI, agents, Alembic, tests
├── frontend/           # Next.js
├── .github/workflows/  # ci.yml
├── docker-compose.yml
├── .env.example
├── AGENTS.md
└── README.md
```
