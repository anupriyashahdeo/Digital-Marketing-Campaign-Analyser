# Build order

We build one step at a time. Each later step is already in the code but **commented out**
at the places listed. Search the repo for `STEP 2+` to find every switch.

## Step 1 — Login (active now)
Sign up, sign in, sign out, forgot password, reset password. Email is the username.

| Part | File |
|---|---|
| Pages | `apps/web/src/pages/` (Login, Signup, ForgotPassword, ResetPassword, Home) |
| Routes | `apps/web/src/App.tsx` |
| Calls to the API | `apps/web/src/api/client.ts` |
| API endpoints | `apps/api/src/ada/api/v1/auth.py` |
| Passwords and tokens | `apps/api/src/ada/security/` |
| Users table | `apps/api/src/ada/db/models/__init__.py` (`User`) |
| Tests | `apps/api/tests/unit/test_auth.py` |

Still to do before production: send real emails (replace `ConsoleMailer`), and move
the login-attempt counter into Redis.

## Step 2 — Dashboard and start a run (done)
Signup creates a personal workspace (same transaction). All data belongs to a workspace;
`Membership.role` is owner / editor / viewer. New users land on a welcome screen with the
first-analysis form; after that the dashboard shows summary tiles and recent analyses.

| Part | File |
|---|---|
| Tables | `db/models`: `Workspace`, `Membership`, `Run`; migration in `alembic/versions/` |
| Access rules | `security/deps.py`: `workspace_member` (404 for non-members), `require_role` |
| Endpoints | `api/v1/workspaces.py` (list, dashboard), `api/v1/runs.py` (list, create, get, cancel) |
| Input rules | `api/schemas` (lengths, regions, languages, keyword clean-up) |
| Pages | `pages/Dashboard.tsx`, `Runs.tsx`, `NewRun.tsx`, `RunDetail.tsx`, `components/AppShell.tsx` |
| Tests | `tests/unit/test_workspaces.py` |

Limits: 3 analyses in progress per workspace (`MAX_ACTIVE_RUNS`). Runs stay `queued` until
Step 3 adds the worker that picks them up.

## Step 3 — Collect ads
YouTube adapter and CSV import (`providers/youtube`, `providers/manual`, `imports` router).
Needs Redis and the worker in `docker-compose.yml`, plus the `Ad` table.

## Step 4 — Turn ads into text
Transcripts, on-screen text, landing pages (`pipeline/to_text.py`, `providers/stt`,
`providers/vision`). Needs MinIO (file storage) and the `AdText` table.

## Step 5 — Ask questions and double-check
Jev answers fixed questions, Claude re-checks low-confidence answers
(`pipeline/analyse.py`, `providers/decision`, `providers/reviewer`). `AnswerRow`, `CostEntry`
tables. Switch on `tests/unit/test_pipeline.py` in `tests/conftest.py`.

## Step 6 — Score and show
Winner / Watch / Dog labels and the dashboard (`domain/scoring`, `events` router).
`ScoreRow` table. Switch on `test_baseline.py` and `test_labeler.py`.
