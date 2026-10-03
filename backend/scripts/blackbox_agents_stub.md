# Black-box stub: shared ChatOpenAI client (#75)

Prerequisite: `docker compose up`, `OPENAI_API_KEY` in `.env`, cookie jar for later cases.

| # | Case | Request | Pass if |
|---|------|---------|---------|
| 1 | Health | `GET /health` | 200, `{"status":"ok"}` |
| 2 | Agent run, no cookie | `POST /api/v1/projects/{uuid}/agents/run` | 401 |
| 3 | Register | `POST /api/v1/auth/register` | 201, cookie set |
| 4 | Create project | `POST /api/v1/projects/` | 201 |
| 5 | Requirement Analyzer | `POST /api/v1/projects/{id}/agents/run` | 200, GET project has `ai_opinion`, GET tasks are `backlog` |
| 6 | Roster + sprints | `POST /api/v1/team-members/`, `POST /api/v1/sprints/` | 201 |
| 7 | Sprint Planner | `POST /api/v1/projects/{id}/agents/plan-sprint` | 200 |
| 8 | Risk Analyzer | `POST /api/v1/projects/{id}/agents/analyze-risk` | 200 |
| 9 | Flags persisted | `GET /api/v1/tasks/?project_id=` | every task `risk_flag` is `true` or `false` (not `null`) |
