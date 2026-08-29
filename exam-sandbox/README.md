# AI Exam Integrity Sandbox

Built for the Daytona Hacksprint.

**Problem:** Universities struggle with cheating in online exams — face-recognition
proctoring is invasive and easy to game.

**Solution:** Every student's exam runs behind its own real [Daytona](https://daytona.io)
sandbox. Integrity signals (tab switching, copy/paste, idle time, devtools) are collected
client-side, then at submit time they're shipped **into the student's own sandbox**, where
an AI risk-scoring agent runs in isolation and returns a suspicion score before the sandbox
is torn down. A live teacher dashboard shows every student's status and flags in real time.

## Why Daytona, specifically

Instead of just bolting on face recognition, each student's post-exam behavioral analysis
executes inside its own disposable, isolated Daytona sandbox — so no student's session can
interfere with another's, and the scoring logic never runs on a shared, tamperable process.
It's real per-student compute isolation, not a gimmick.

## Architecture

- **Frontend:** plain HTML/CSS/JS served by Flask (no build step)
- **Backend:** Flask (`app.py`) + SQLite (`exam.db`, gitignored)
- **Sandbox layer:** `daytona_sandbox.py` wraps the Daytona Python SDK
  - `daytona.create(network_block_all=True)` → one network-isolated sandbox per exam session
  - `sandbox.process.code_run(...)` → runs the risk-scoring agent inside the sandbox, and
    also runs the student's own submission for the coding question (Q7) — a real,
    hard network cutoff, not a heuristic
  - `daytona.delete(sandbox)` → cleans up on submit
- If the Daytona API is unreachable, the app falls back to local scoring so a live demo
  never hard-crashes (`sandbox_status` shows `error` in that case, for transparency).

## Setup

```bash
pip install -r requirements.txt
```

Requires `DAYTONA_API_KEY` in the environment. This project's `.env` loading walks up to
`C:\Daytona\.env` automatically (`load_dotenv()` searches parent directories), so if you
already set your key there for the root starter script, nothing else to do. Otherwise:

```bash
copy .env.example .env
```

and fill in your key.

## Run

```bash
python app.py
```

- Student flow: http://localhost:5000/
- Teacher dashboard: http://localhost:5000/dashboard

## Demo script (2 minutes)

1. Open `/` in one tab, log in as a student → sandbox spins up (status badge goes green).
2. Answer a couple of questions.
3. Switch to another tab, or copy/paste into an answer → banner flags it instantly.
4. Open `/dashboard` in a second tab/window → see the student listed live, flag count
   ticking up.
5. Submit the exam → sandbox is torn down, dashboard shows a computed risk verdict
   (clear / suspicious / high_risk). Click **View** for the full per-student report:
   answers + timestamped activity log.

## Deploying to Render (a public, persistent link)

This app is a stateful Flask + SQLite server, not a static site or a set of serverless
functions — it needs to run as a normal long-lived process with real disk. That rules out
Vercel-style serverless hosting (each request can hit a fresh, stateless instance with no
shared disk, which would silently break the SQLite-backed session/flag/dashboard data).
[Render](https://render.com)'s free Web Service tier runs Flask the way it's meant to run.

The repo already has what Render needs:
- `requirements.txt` includes `gunicorn` (a production WSGI server; note it's Linux-only,
  so it won't run if you try it locally on Windows — that's expected, `python app.py` is
  still the right way to run this locally)
- `Procfile`: `web: gunicorn app:app --bind 0.0.0.0:$PORT`
- `app.py` initializes the database on import, so it works under gunicorn (not just when
  run directly with `python app.py`)

Steps (do these yourself in Render's dashboard — this session won't create accounts or
enter your API key into forms on your behalf):

1. Sign up at [render.com](https://render.com) and connect your GitHub account.
2. **New +** → **Web Service** → pick `marcuslew/daytona-marcus-benjamin`.
3. **Root Directory:** `exam-sandbox`
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT` (Render also auto-detects
   this from the `Procfile`, so you can usually leave it default)
6. **Environment** tab → add:
   - `DAYTONA_API_KEY` = your key (from app.daytona.io → Keys)
   - `FLASK_SECRET_KEY` = any random string
7. Deploy. Render gives you a permanent `https://<your-service>.onrender.com` URL.

Caveats to know about, honestly:
- The free tier spins the service down after ~15 minutes of no traffic and takes ~30-50s
  to wake back up on the next request — fine for demoing, just expect a cold-start delay
  if it's been idle.
- The free tier's filesystem isn't a *persistent disk* — a redeploy or a long idle-then-wake
  cycle can reset `exam.db`. For a hackathon demo window this is low-risk, but don't expect
  data to survive indefinitely; it's not a substitute for a real database in production.

## Judging criteria mapping

- **Completeness:** full working flow — login → sandboxed exam → live monitoring →
  teacher dashboard → per-student report.
- **Innovation:** uses sandbox *isolation* as the integrity mechanism, not just
  webcam/face-recognition proctoring.
- **Real-life problem:** online exam cheating is a widespread, costly problem for
  universities running remote assessments.
- **Sponsor usage:** real Daytona SDK calls create, execute inside, and delete a genuine
  sandbox per student — not a mock.
