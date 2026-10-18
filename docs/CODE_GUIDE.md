# Code guide

How the code fits together, where each feature lives, and what is dormant for now.
All paths are relative to `ad-campaign-analyser/`.

## 1. Big picture

```
Browser (React, :5173)                      API (FastAPI, :8000)                 DB (SQLite dev / Postgres)
──────────────────────                      ────────────────────                 ─────────────────────────
main.tsx
 └ AuthProvider  ── GET /auth/me ─────────▶ api/v1/auth.py ──────────────────▶ users
    └ App.tsx (routes)
       └ Protected → WorkspaceProvider ─ GET /workspaces ─▶ api/v1/workspaces.py ▶ workspaces, memberships
          └ AppShell (top bar + <Outlet/>)
             ├ /            Dashboard ─ GET /workspaces/{id}/dashboard ─▶ workspaces.py ▶ runs (counts)
             ├ /runs        Runs      ─ GET /workspaces/{id}/runs ──────▶ api/v1/runs.py ▶ runs
             ├ /runs/new    NewRun    ─ POST /workspaces/{id}/runs
             ├ /runs/:id    RunDetail ─ GET  …/runs/{id}, POST …/cancel
             └ /youtube     YouTube   ─ GET /workspaces/{id}/youtube/search ▶ api/v1/youtube.py ▶ YouTube Data API
```

Vite proxies `/api/*` to `localhost:8000` (`apps/web/vite.config.ts`), so the browser only talks
to one origin and the session cookie just works.

## 2. One request, end to end (the dashboard)

1. **`apps/web/src/pages/Dashboard.tsx`**: on mount, `load()` calls `api.dashboard(workspace.id)`.
   While any run is queued or running, `usePoll` calls it again every 10 seconds.
2. **`apps/web/src/api/client.ts`**: `request()` does `fetch("/api/v1/workspaces/{id}/dashboard")`
   with the cookie. On 401 it calls the sign-out handler. On error it throws `ApiError(status, message)`.
3. **`apps/api/src/ada/main.py`**: the router is mounted under `/api/v1`, and the middleware adds security headers.
4. **`apps/api/src/ada/security/deps.py`**: `workspace_member` → `current_user` reads the
   `ada_session` cookie, checks the JWT, loads the `User`, and then loads that user's `Membership` for the
   workspace. A non-member gets a 404.
5. **`apps/api/src/ada/api/v1/workspaces.py` → `dashboard()`**: runs the COUNT/SUM queries on `Run`
   and returns the 5 most recent runs.
6. **`apps/api/src/ada/api/schemas/__init__.py`**: `DashboardOut` shapes the JSON:

```json
{
  "workspace": {"id": 1, "name": "pavithra's workspace", "region": "IN", "role": "owner"},
  "stats": {"total_runs": 3, "active_runs": 1, "completed_runs": 0, "ads_analysed": 0,
            "spent_this_month_usd": 0.0, "run_spend_cap_usd": 5.0},
  "recent_runs": [{"id": 3, "category": "running shoes", "keywords": ["Nike"], "status": "queued", "...": "..."}],
  "can_edit": true
}
```

7. Back in `Dashboard.tsx`, `total_runs === 0` shows `<Welcome>` (the first-run form). Otherwise it
   shows 4 `<Tile>`s and `<RunsTable runs={recent_runs}>`.

Every other feature follows the same pattern: **page → `api.*` in client.ts → router in `api/v1/` →
`workspace_member` → DB query → Pydantic schema → JSON → page state**.

## 3. Feature map

| Feature | Frontend | Backend endpoint | Returns |
|---|---|---|---|
| Sign up / in / out, reset | `pages/Login, Signup, ForgotPassword, ResetPassword`, `auth/AuthContext.tsx` | `api/v1/auth.py` | `User {id, email}` and the cookie |
| Workspace picker | `workspace/WorkspaceContext.tsx`, `AppShell.tsx` | `GET /workspaces` | `Workspace[]` |
| Dashboard | `pages/Dashboard.tsx` | `GET /workspaces/{id}/dashboard` | `DashboardOut` (above) |
| List analyses | `pages/Runs.tsx`, `components/RunsTable.tsx` | `GET …/runs?limit&offset&status` | `RunPage {items,total,limit,offset}` |
| Start analysis | `features/runs/NewRunForm.tsx` | `POST …/runs` | `RunOut` (status `queued`, max 3 active) |
| Analysis detail / cancel | `pages/RunDetail.tsx` | `GET …/runs/{id}`, `POST …/runs/{id}/cancel` | `RunOut` |
| **YouTube explorer** | `pages/YouTube.tsx` | `GET …/youtube/search?q&limit&order&language` | `YouTubeSearchOut` (below) |

Access rules: viewers can read; owners and editors can create or cancel (`require_role` in `security/deps.py`).

## 4. YouTube explorer (new)

**What it does:** you type keywords (e.g. `running shoes ad`) or paste one or more video links or IDs.
The API calls the official YouTube Data API v3 and returns public stats. Nothing is downloaded.

```
YouTube.tsx ──▶ api.youtubeSearch() ──▶ api/v1/youtube.py: search()
                                           ├ video_ids_in(q)  → links/ids?  → yt.get_videos(ids)   (1 quota unit)
                                           └ otherwise                     → yt.search(q, region) (≈101 units)
                                                                                └ search.list → videos.list
                                           ├ _out(): adds url + engagement_rate = (likes+comments)/views
                                           └ _summary(): count, total/avg views, avg engagement, top video
```

| Piece | File |
|---|---|
| HTTP client, error messages, 15-min search cache | `apps/api/src/ada/providers/youtube/client.py` |
| Shared client (None if no key) | `apps/api/src/ada/providers/registry.py` → `get_youtube()` |
| Contract | `apps/api/src/ada/spi/video_metadata.py` (`VideoMeta`, `VideoMetadataSource`) |
| Route + link parsing + summary | `apps/api/src/ada/api/v1/youtube.py` |
| Page (tiles, sortable table, CSV) | `apps/web/src/pages/YouTube.tsx` |
| Tests | `apps/api/tests/unit/test_youtube.py` |

Response:
```json
{
  "query": "running shoes", "mode": "search",
  "videos": [{"video_id": "abc…", "url": "https://www.youtube.com/watch?v=abc…", "title": "…",
              "channel_title": "Nike", "thumbnail_url": "…", "published_at": "2026-01-01T00:00:00Z",
              "duration_seconds": 30, "views": 1000, "likes": 40, "comments": 10,
              "engagement_rate": 0.05}],
  "summary": {"count": 2, "total_views": 4000, "avg_views": 2000,
              "avg_engagement_rate": 0.03, "top_video_id": "bbb…"}
}
```

Errors: no key → 503 "Add YOUTUBE_API_KEY…"; bad key / quota used up / YouTube down → 502 with a
plain message, which the page shows in its error box.

**Setup:** Google Cloud Console → create a project → enable "YouTube Data API v3" → Credentials →
API key → paste it into `.env` as `YOUTUBE_API_KEY=…` and restart uvicorn. The free quota is 10,000 units a day.

## 5. What's dormant or unneeded right now (cleanup list)

**Safe to delete:**
- `d:\Work\ad-campaign-analyser\apps`, `docs`, `eval`, `infra`, `scripts`, `README.md`, `Makefile`,
  `docker-compose*.yml`, `.github`, `.gitignore` in the **outer** folder: an older copy of this
  project (no auth, no workspaces). Keep the outer `.env.example` (copy it inside first) and the
  `.Ad_Campaign` virtualenv.
- `apps/api/package-lock.json`: an npm file in the Python app, probably from an accidental `npm install`.
- `apps/web/dist/`, `apps/api/.ruff_cache/`, `apps/api/.pytest_cache/`: build and tool caches
  (already gitignored, regenerated on demand).
- `apps/web/src/hooks/useSSE.ts`: not used anywhere (it only pairs with the fake `events.py` stream).

**Keep but ignore for now (Step 3+, not wired into `main.py`):**
- Empty packages: `providers/adfeed`, `providers/stt`, `providers/vision`, `storage`,
  `db/repositories`, `domain/insights`.
- `api/v1/events.py` (fake progress stream) and `api/v1/imports.py` (CSV import, not workspace-scoped).
- `workers/` (Celery), `pipeline/` (to_text, analyse), `cache/`, `cost/`, `domain/questions`,
  `domain/scoring`, `providers/decision/*`, `providers/reviewer/*`, `providers/manual`.
- `infra/`, `docker-compose*.yml`, `.github/workflows/ci.yml`: only needed for Docker or CI.
- Commented-out tables in `db/models/__init__.py` and skipped tests in `tests/conftest.py`.

## 6. Change log

| Date | Change |
|---|---|
| 2026-10-18 | Added the YouTube explorer: `providers/youtube/client.py`, `api/v1/youtube.py`, schemas, `get_youtube()` in the registry, `pages/YouTube.tsx`, nav link and route, dashboard button, `components/Tile.tsx` (moved out of Dashboard), formatters (`fmtCompact`, `fmtPct`, `fmtDuration`), CSS, 7 tests. Extended `VideoMeta` with `channel_title`, `thumbnail_url`, `duration_seconds` and replaced the unused `channel_recent` with `search`. Documented in ROADMAP (Step 2b) and this guide. |
