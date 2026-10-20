# Deploying: get a permanent public link

The app goes live as **one service** on [Render](https://render.com) with a free Postgres
database on [Neon](https://neon.tech). Both are free and need no credit card.

```
Browser ──https──> Render (Dockerfile: website + API in one container) ──> Neon (Postgres)
                                                  └──> YouTube Data API
```

How it fits together:
- `Dockerfile` builds the React site, then puts it inside the Python API image.
  FastAPI serves the site *and* `/api/v1/...` from the same URL (`WEB_DIST` in `main.py`).
- On every start, `alembic upgrade head` creates or updates the database tables.
- `render.yaml` tells Render how to build and run it.

## One-time setup (about 20 minutes)

### 1. Put the code on GitHub
Render deploys from a GitHub repo.
1. Create an empty repo at https://github.com/new (e.g. `ad-campaign-analyser`). It can be private.
2. In this folder:
   ```bash
   git add -A
   git commit -m "Add production deploy (Render + Neon)"
   git remote add origin https://github.com/<your-username>/ad-campaign-analyser.git
   git push -u origin HEAD
   ```
   `HEAD` pushes whatever branch you're on. Render deploys the branch you pick in step 3,
   so choose this one (or merge it into `main` first and pick `main`).
   `.env` (your secrets) is in `.gitignore`, so it is **not** uploaded. Keep it that way.

### 2. Create the database on Neon
1. Sign up at https://neon.tech (GitHub login is fine).
2. Create a project. Pick region **AWS Asia Pacific (Singapore)**, which is closest to Render's Singapore region.
3. On the dashboard, click **Connect** and copy the connection string. It looks like
   `postgresql://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
   The app converts it to the driver format it needs; paste it as-is.

### 3. Create the service on Render
1. Sign up at https://render.com with your GitHub account.
2. Click **New → Blueprint**, then pick your repo. Render finds `render.yaml`.
3. It asks for the values marked `sync: false`:
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Neon string from step 2 |
   | `YOUTUBE_API_KEY` | same key as in your local `.env` |
   | `FRONTEND_URL` | `https://ad-campaign-analyser.onrender.com` (fix it in step 4 if your URL differs) |
   `JWT_SECRET` is generated for you.
4. Click **Apply**. The first build takes 3–5 minutes. Watch the **Logs** tab.
5. Your permanent link is at the top of the service page:
   `https://ad-campaign-analyser.onrender.com` (or similar). If it differs from
   `FRONTEND_URL`, update that variable under **Environment** (password-reset links use it).

Check it works: open `<your-url>/health`. It should return `{"status":"ok",...}`.

## Updating the live site
Push to GitHub and Render redeploys automatically:
```bash
git add -A
git commit -m "Describe the change"
git push
```

## Good to know
- **Free tier sleeps.** After 15 minutes with no visitors the service stops; the next visit
  takes about 50 seconds to wake it. Render's paid Starter plan ($7/month) stays awake.
- **Forgot-password emails** are printed to the Render **Logs** (`MAIL_PROVIDER=console`).
  To send real email, add `MAIL_PROVIDER=smtp` and the `SMTP_*` variables from `config.py`.
- **YouTube quota** (10,000 units/day) is shared by everyone using the site.
- **Secrets** live only in Render's Environment tab, never in git.
- **Something broke?** Render → your service → **Logs**. A startup error such as
  `Set JWT_SECRET` or a database connection error shows up there.

## Test the production image on your machine (optional)
```bash
docker build -t ada-prod .
docker run --rm -p 8099:8000 -e DATABASE_URL=<a postgres url> -e JWT_SECRET=<32+ random chars> ada-prod
```
Then open http://localhost:8099.
