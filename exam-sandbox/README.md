# AI Exam Integrity Sandbox

Built for the Daytona Hacksprint.

**Problem:** Universities struggle with cheating in online exams — face-recognition
proctoring is invasive and easy to game.

**Solution:** Every student's exam runs behind its own real [Daytona](https://daytona.io)
sandbox. Integrity signals (tab switching, copy/paste, idle time, devtools) are collected
client-side, then at submit time they're shipped **into the student's own sandbox**, where
an AI risk-scoring agent runs in isolation and returns a suspicion score before the sandbox
is torn down. A live teacher dashboard shows every student's status and flags in real time.

## Live demo

- Student flow: https://daytona-marcus-benjamin.onrender.com/
- Teacher dashboard: https://daytona-marcus-benjamin.onrender.com/dashboard

(Hosted on Render's free tier — the service spins down after ~15 minutes of no traffic, so
the first request after a while may take 30-50s to wake it back up.)

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

## Judging criteria mapping

- **Completeness:** full working flow — login → sandboxed exam → live monitoring →
  teacher dashboard → per-student report.
- **Innovation:** uses sandbox *isolation* as the integrity mechanism, not just
  webcam/face-recognition proctoring.
- **Real-life problem:** online exam cheating is a widespread, costly problem for
  universities running remote assessments.
- **Sponsor usage:** real Daytona SDK calls create, execute inside, and delete a genuine
  sandbox per student — not a mock.
