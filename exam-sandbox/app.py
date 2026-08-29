"""
AI Exam Integrity Sandbox -- Flask backend.

Each exam session gets its own Daytona sandbox (created on /api/exam/start).
Client-side JS reports integrity flags (tab switches, copy/paste, idle time,
devtools) to /api/flag. On submit, the flags are analyzed by an AI agent
running INSIDE the student's own Daytona sandbox, then the sandbox is torn
down. Teachers watch it all live on /dashboard.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

load_dotenv()  # walks up to C:\Daytona\.env for DAYTONA_API_KEY

import daytona_sandbox as dsb
from questions import QUESTIONS

DB_PATH = os.path.join(os.path.dirname(__file__), "exam.db")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")


# ---------------------------------------------------------------- database

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            sandbox_id TEXT,
            sandbox_status TEXT DEFAULT 'pending',
            status TEXT DEFAULT 'in_progress',
            started_at TEXT,
            submitted_at TEXT,
            risk_score INTEGER DEFAULT 0,
            risk_verdict TEXT DEFAULT 'clear'
        );

        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            answer TEXT,
            UNIQUE(session_id, question_id)
        );

        CREATE TABLE IF NOT EXISTS flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            flag_type TEXT NOT NULL,
            detail TEXT,
            ts TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def local_risk_fallback(flags):
    """Used only if the Daytona API call fails, so a live demo never hard-crashes."""
    tab = sum(1 for f in flags if f["type"] == "tab_switch")
    cp = sum(1 for f in flags if f["type"] in ("copy", "paste", "cut"))
    idle = sum(1 for f in flags if f["type"] == "idle")
    devtools = sum(1 for f in flags if f["type"] == "devtools")
    network = sum(1 for f in flags if f["type"] == "network_block_triggered")
    score = min(tab * 15 + cp * 25 + idle * 5 + devtools * 30 + network * 40, 100)
    verdict = "high_risk" if score >= 60 else ("suspicious" if score >= 25 else "clear")
    return score, verdict


# ---------------------------------------------------------- student routes

@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    name = request.form.get("name", "").strip()
    student_id = request.form.get("student_id", "").strip()
    if not name or not student_id:
        return render_template("login.html", error="Name and Student ID are required.")

    session_id = str(uuid.uuid4())
    db = get_db()
    db.execute(
        "INSERT INTO exam_sessions (id, student_name, student_id, started_at) VALUES (?, ?, ?, ?)",
        (session_id, name, student_id, now_iso()),
    )
    db.commit()

    session["exam_session_id"] = session_id
    session["student_name"] = name
    return redirect(url_for("exam_page"))


@app.route("/exam")
def exam_page():
    if "exam_session_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("exam.html", student_name=session["student_name"], questions=QUESTIONS)


@app.route("/api/exam/start", methods=["POST"])
def api_exam_start():
    session_id = session.get("exam_session_id")
    if not session_id:
        return jsonify({"error": "no active session"}), 401

    db = get_db()
    try:
        sandbox_id = dsb.create_exam_sandbox()
        db.execute(
            "UPDATE exam_sessions SET sandbox_id = ?, sandbox_status = 'active' WHERE id = ?",
            (sandbox_id, session_id),
        )
        db.commit()
        return jsonify({"sandbox_id": sandbox_id, "status": "active"})
    except Exception as exc:
        db.execute("UPDATE exam_sessions SET sandbox_status = 'error' WHERE id = ?", (session_id,))
        db.commit()
        return jsonify({"status": "error", "message": str(exc)})


@app.route("/api/exam/answer", methods=["POST"])
def api_exam_answer():
    session_id = session.get("exam_session_id")
    if not session_id:
        return jsonify({"error": "no active session"}), 401

    data = request.get_json(force=True)
    question_id = data.get("question_id")
    answer = data.get("answer", "")

    db = get_db()
    db.execute(
        """INSERT INTO answers (session_id, question_id, answer) VALUES (?, ?, ?)
           ON CONFLICT(session_id, question_id) DO UPDATE SET answer = excluded.answer""",
        (session_id, question_id, answer),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/exam/run_code", methods=["POST"])
def api_exam_run_code():
    session_id = session.get("exam_session_id")
    if not session_id:
        return jsonify({"error": "no active session"}), 401

    data = request.get_json(force=True)
    code = data.get("code", "")

    db = get_db()
    row = db.execute(
        "SELECT sandbox_id, sandbox_status FROM exam_sessions WHERE id = ?", (session_id,)
    ).fetchone()

    if not row or not row["sandbox_id"] or row["sandbox_status"] != "active":
        return jsonify({"ok": False, "output": "Sandbox not available.", "network_blocked": False})

    try:
        output, network_blocked = dsb.run_student_code(row["sandbox_id"], code)
    except Exception as exc:
        output, network_blocked = f"Execution error: {exc}", False

    if network_blocked:
        db.execute(
            "INSERT INTO flags (session_id, flag_type, detail, ts) VALUES (?, ?, ?, ?)",
            (session_id, "network_block_triggered", "Submitted code attempted outbound network access", now_iso()),
        )
        db.commit()

    return jsonify({"ok": True, "output": output, "network_blocked": network_blocked})


@app.route("/api/flag", methods=["POST"])
def api_flag():
    session_id = session.get("exam_session_id")
    if not session_id:
        return jsonify({"error": "no active session"}), 401

    data = request.get_json(force=True)
    flag_type = data.get("type", "unknown")
    detail = data.get("detail", "")

    db = get_db()
    db.execute(
        "INSERT INTO flags (session_id, flag_type, detail, ts) VALUES (?, ?, ?, ?)",
        (session_id, flag_type, detail, now_iso()),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/exam/submit", methods=["POST"])
def api_exam_submit():
    session_id = session.get("exam_session_id")
    if not session_id:
        return jsonify({"error": "no active session"}), 401

    db = get_db()
    row = db.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
    flag_rows = db.execute(
        "SELECT flag_type as type, detail, ts FROM flags WHERE session_id = ?", (session_id,)
    ).fetchall()
    flags = [dict(r) for r in flag_rows]

    sandbox_status = row["sandbox_status"]
    if row["sandbox_id"] and row["sandbox_status"] == "active":
        try:
            score, verdict = dsb.run_risk_analysis(row["sandbox_id"], flags)
        except Exception:
            score, verdict = local_risk_fallback(flags)
        try:
            dsb.cleanup_sandbox(row["sandbox_id"])
            sandbox_status = "deleted"
        except Exception:
            sandbox_status = "cleanup_error"
    else:
        score, verdict = local_risk_fallback(flags)

    db.execute(
        """UPDATE exam_sessions
           SET status = 'submitted', submitted_at = ?, risk_score = ?, risk_verdict = ?, sandbox_status = ?
           WHERE id = ?""",
        (now_iso(), score, verdict, sandbox_status, session_id),
    )
    db.commit()

    session.pop("exam_session_id", None)
    session.pop("student_name", None)
    return jsonify({"risk_score": score, "risk_verdict": verdict})


# ---------------------------------------------------------- teacher routes

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/api/dashboard")
def api_dashboard():
    db = get_db()
    rows = db.execute(
        """SELECT s.*,
                  (SELECT COUNT(*) FROM flags f WHERE f.session_id = s.id) as flag_count
           FROM exam_sessions s
           ORDER BY s.started_at DESC"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/dashboard/session/<session_id>")
def api_dashboard_session(session_id):
    db = get_db()
    sess = db.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
    if not sess:
        return jsonify({"error": "not found"}), 404
    answers = db.execute(
        "SELECT question_id, answer FROM answers WHERE session_id = ?", (session_id,)
    ).fetchall()
    flags = db.execute(
        "SELECT flag_type as type, detail, ts FROM flags WHERE session_id = ? ORDER BY ts", (session_id,)
    ).fetchall()
    return jsonify(
        {
            "session": dict(sess),
            "answers": [dict(a) for a in answers],
            "flags": [dict(f) for f in flags],
            "questions": QUESTIONS,
        }
    )


# Runs on import so the schema exists whether launched via `python app.py`
# (local dev) or a production WSGI server like gunicorn (which imports this
# module and never executes the __main__ block below).
init_db()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
