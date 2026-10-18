# Ad Campaign Analyser

Find YouTube ads -> turn into text -> ask fixed questions -> double-check -> score -> dashboard/report.

## Current step: login only
We are building one step at a time. See [docs/ROADMAP.md](docs/ROADMAP.md).
Everything after login is commented out (search for `STEP 2+`).

### Run it on your machine (no Docker)
Terminal 1 - API (uses a local SQLite file, no database setup needed):
```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn ada.main:app --reload --port 8000
```
Terminal 2 - website:
```bash
cd apps/web
npm install
npm run dev
```
Open http://localhost:5173. Forgot-password links are printed in Terminal 1.

Tests: `cd apps/api && pytest -q`

### Or with Docker (PostgreSQL)
```bash
cp .env.example .env
make dev
```

## Status
Foundation built: SPI contracts, scoring labeler, analyse+escalation pipeline, cache,
spend cap, manual CSV import, DB models, FastAPI skeleton, Celery wiring, React shell.
Stubs to implement: Jev/Claude clients, YouTube adapter, STT/vision, ad-feed adapter,
persistence in tasks, reports, auth/RBAC, OAuth. See docs/ and the build order.

[Verify] items: Jev/TypeSafe API, YouTube quota, ad-feed terms, Hindi accuracy.
Do not download competitor video/audio without legal sign-off.

## Authentication
Email is the username. Endpoints under `/api/v1/auth`: `signup`, `login`, `logout`, `me`,
`forgot-password`, `reset-password`. Passwords are hashed with scrypt; sessions use an
httpOnly cookie; reset links are single-use and expire in 30 minutes. In dev the reset link is
printed in the API log (ConsoleMailer). **Before production:** set `JWT_SECRET`, plug a real
mailer (SES/SendGrid) into `spi/mailer.py`, and move login throttling to Redis.

## Push to GitHub
```bash
git remote add origin https://github.com/<your-username>/ad-campaign-analyser.git
git push -u origin main
```
