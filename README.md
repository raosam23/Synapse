# Synapse

AI-powered scrum for teams that paste requirements and get a living backlog, fixed **2-week** sprints, and a board that keeps pulling work until the project is done.

Not a chatbot wrapper — the product is the **agent loop + backlog + sprint board + comments**.

| Backend | Frontend | Database | Tooling |
| --- | --- | --- | --- |
| FastAPI · SQLModel · Alembic · Python 3.12+ | Next.js · React · Bun | Postgres 15 (Compose) | `uv` · Docker · GitHub Actions |

Product behavior for **v1.0.0** lives in [`AGENTS.md`](./AGENTS.md).

---

## Repository

```text
Synapse/
├── backend/          # FastAPI API, models, Alembic
├── frontend/         # Next.js app
├── .github/          # CI + issue templates
├── docker-compose.yml
├── .env.example
├── AGENTS.md
└── README.md
```

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (Compose v2)
- [uv](https://docs.astral.sh/uv/) (Python 3.12+)
- [Bun](https://bun.sh/) (frontend)

---

## Quick start (recommended)

Run Postgres in Docker; run API and UI on the host. This matches `.env.example` (`localhost`).

### 1. Env

```bash
cp .env.example .env
```

`.env` is gitignored. Defaults in `.env.example` are for local only — do not commit real secrets.

### 2. Database

```bash
docker compose up database -d
```

Postgres listens on `localhost:${POSTGRES_PORT}` (default `5432`). A fresh volume also creates `synapse_test` (pytest). If Postgres was already initialized before that init script existed:

```bash
docker compose exec database psql -U "$POSTGRES_USER" -c "CREATE DATABASE synapse_test;"
```

### 3. Backend — install, migrate, run

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

- API: [http://localhost:8000](http://localhost:8000)
- Health: [http://localhost:8000/health](http://localhost:8000/health) → `{"status":"ok"}`
- OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

`DATABASE_URL` must use the `postgresql+asyncpg://` scheme. Alembic rewrites it to `psycopg` for sync migrations automatically.

Local **uvicorn / Swagger** uses `DATABASE_URL` → `synapse_db`. **pytest** uses `TEST_DATABASE_URL` → `synapse_test` on the same Postgres. API tests `TRUNCATE` only the test database, so running pytest does not wipe accounts you created in Swagger. CI uses its own ephemeral `synapse_ci` via `DATABASE_URL` (no `TEST_DATABASE_URL`).

### 4. Frontend

```bash
cd frontend
bun install
bun run dev
```

UI: [http://localhost:3000](http://localhost:3000)

---

## Full stack via Compose

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Postgres | localhost:5432 |

The Compose backend uses hostname `database` in `DATABASE_URL` (not `localhost`).

Migrations are **not** applied on container start. After Postgres is up:

```bash
# from the host (uses localhost URL in .env)
cd backend && uv sync && uv run alembic upgrade head

# or inside the backend container
docker compose exec backend uv run alembic upgrade head
```

---

## Authentication

Auth is a JWT stored in an httpOnly cookie named `access_token` (`samesite=lax`). Register and login set the cookie and return the user object only — the token is **not** in the JSON body. `projects`, `team-members`, `sprints`, `tasks`, `task-dependencies`, and `GET /api/v1/auth/me` all require that cookie.

```bash
# Cookie jar so later requests send access_token
# 1. Register (201 + Set-Cookie; you are already logged in)
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "jennie@example.com", "password": "supersecret123", "name": "Jennie"}'
# -> {"id": "...", "email": "jennie@example.com", "name": "Jennie", "created_at": "..."}

# 2. Or log in (200 + Set-Cookie) if you already have an account
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "jennie@example.com", "password": "supersecret123"}'

# 3. Call a protected endpoint (send the cookie)
curl -b cookies.txt http://localhost:8000/api/v1/tasks/

# Check who you're logged in as
curl -b cookies.txt http://localhost:8000/api/v1/auth/me

# Log out: revoke the JWT (jti is stored in revoked_tokens) and clear the cookie
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/v1/auth/logout
```

In [Swagger UI](http://localhost:8000/docs), call **register** or **login** from the browser first. The browser stores `access_token`; later **Try it out** requests on the same origin send it automatically. The **Authorize** button (Bearer header) does nothing for this API — there is no `Authorization` header.

Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (see `.env.example`). Logout is `POST /api/v1/auth/logout`: the server blocklists the token and deletes the cookie. A revoked token is rejected even if you still have the cookie value.

---

## Useful Alembic commands

From `backend/`:

```bash
uv run alembic current          # applied revision
uv run alembic upgrade head     # apply pending migrations
uv run alembic downgrade -1     # roll back one revision
uv run alembic history          # revision timeline
```

Schema changes: update SQLModel tables under `backend/app/models/`, then:

```bash
uv run alembic revision --autogenerate -m "short description"
uv run alembic upgrade head
```

Review autogenerated scripts before committing.

---

## Development checks

```bash
# backend
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest   # migrates synapse_test if needed; does not empty synapse_db

# frontend
cd frontend
bun run lint
```

CI runs lint, tests, and Docker image builds on PRs to `main`. The `test` job starts an ephemeral Postgres 15.4 service (`synapse_ci`) with throwaway credentials hardcoded in the workflow (not `.env` and not GitHub secrets), runs `alembic upgrade head`, then pytest. In CI the database host is `localhost`, not the Compose hostname `database`. Local pytest does not use `synapse_ci`; it uses `TEST_DATABASE_URL`.

---

## Current status

Early **v1.0.0** build-out: schema includes `users`, `projects`, `team_members`, `sprints`, `tasks`, and `task_dependencies`. Team members, sprints, and tasks belong to a project (`project_id`); list them with `?project_id=`. `POST /api/v1/sprints/` generates consecutive 2-week windows from the project duration. A task’s `sprint_id` is optional (null in the backlog) and must point at a sprint on the same project. A team member’s display name is the linked user’s name, or their email if name is missing. Cookie-auth CRUD exists for projects, team members, sprints, tasks, and task dependencies. Comments, agents, and the Kanban UI come next.

See [`AGENTS.md`](./AGENTS.md) for scope, task statuses, and agent roles.
