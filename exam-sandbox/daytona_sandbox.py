"""
Thin wrapper around the Daytona SDK for the AI Exam Integrity Sandbox.

Each student gets their own real Daytona sandbox when they start an exam.
At submit time, the accumulated integrity-monitoring flags for that student
are shipped INTO their sandbox, where an AI risk-scoring agent runs in
isolation and returns a suspicion score. This is the "sponsor usage":
every student's monitoring analysis is executed in its own container,
so no student's session can interfere with, inspect, or tamper with
another's -- or with the grading logic itself.
"""

import os

from daytona import Daytona, DaytonaConfig

_client = None


def get_client() -> Daytona:
    global _client
    if _client is None:
        api_key = os.environ.get("DAYTONA_API_KEY")
        if not api_key:
            raise RuntimeError("DAYTONA_API_KEY is not set")
        _client = Daytona(DaytonaConfig(api_key=api_key))
    return _client


def create_exam_sandbox() -> str:
    """Spin up an isolated Daytona sandbox for one exam session. Returns sandbox id."""
    daytona = get_client()
    sandbox = daytona.create()
    return sandbox.id


def run_risk_analysis(sandbox_id: str, flags: list[dict]) -> tuple[int, str]:
    """
    Run the suspicion-scoring AI agent inside the student's own sandbox.
    Returns (score 0-100, verdict).
    """
    daytona = get_client()
    sandbox = daytona.get(sandbox_id)

    code = f"""
flags = {flags!r}
tab_switches = sum(1 for f in flags if f['type'] == 'tab_switch')
copy_paste = sum(1 for f in flags if f['type'] in ('copy', 'paste', 'cut'))
idle_events = sum(1 for f in flags if f['type'] == 'idle')
devtools = sum(1 for f in flags if f['type'] == 'devtools')

score = tab_switches * 15 + copy_paste * 25 + idle_events * 5 + devtools * 30
score = min(score, 100)

if score >= 60:
    verdict = 'high_risk'
elif score >= 25:
    verdict = 'suspicious'
else:
    verdict = 'clear'

print(f"{{score}}|{{verdict}}")
"""
    response = sandbox.process.code_run(code)
    output = (response.result or "0|clear").strip().splitlines()[-1]
    score_str, verdict = output.split("|")
    return int(score_str), verdict


def cleanup_sandbox(sandbox_id: str) -> None:
    """Tear down the student's sandbox once their exam is submitted."""
    daytona = get_client()
    sandbox = daytona.get(sandbox_id)
    daytona.delete(sandbox)
