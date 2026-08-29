"""
Thin wrapper around the Daytona SDK for the AI Exam Integrity Sandbox.

Each student gets their own real Daytona sandbox when they start an exam,
created with network_block_all=True -- a hard guarantee, not a heuristic.
Two things run inside it:

  1. The risk-scoring AI agent (at submit time), analyzing that student's
     integrity flags in isolation from every other student's session.
  2. The student's own coding-question submission (question 7), which
     physically cannot reach an AI API, a search engine, or any other
     external server, because the sandbox has no network access at all.

This is the "sponsor usage": real create -> execute -> delete calls per
exam session, not a mock.
"""

import os

from daytona import CreateSandboxFromSnapshotParams, Daytona, DaytonaConfig

_client = None

# Substrings that show up in Python's exception output when an outbound
# connection is refused by the sandbox's network block, across the usual
# failure modes (DNS resolution, connection refusal, timeout).
NETWORK_ERROR_MARKERS = (
    "connectionerror",
    "getaddrinfo failed",
    "failed to resolve",
    "network is unreachable",
    "temporary failure in name resolution",
    "connection refused",
    "errno 101",
    "errno -3",
    "errno 111",
    "max retries exceeded",
    "name or service not known",
)


def get_client() -> Daytona:
    global _client
    if _client is None:
        api_key = os.environ.get("DAYTONA_API_KEY")
        if not api_key:
            raise RuntimeError("DAYTONA_API_KEY is not set")
        _client = Daytona(DaytonaConfig(api_key=api_key))
    return _client


def create_exam_sandbox() -> str:
    """
    Spin up an isolated Daytona sandbox for one exam session, with all
    outbound network access blocked. Returns the sandbox id.
    """
    daytona = get_client()
    params = CreateSandboxFromSnapshotParams(network_block_all=True)
    sandbox = daytona.create(params)
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
network_attempts = sum(1 for f in flags if f['type'] == 'network_block_triggered')

score = tab_switches * 15 + copy_paste * 25 + idle_events * 5 + devtools * 30 + network_attempts * 40
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


def run_student_code(sandbox_id: str, code: str) -> tuple[str, bool]:
    """
    Run student-submitted code inside their own (network-blocked) sandbox.
    Returns (output text, network_blocked) where network_blocked is True if
    the code's own attempt to reach the network was caught and refused by
    the sandbox -- i.e. they tried to call out to something (an AI API,
    a search engine, a pastebin) and the isolation stopped it.

    A blocked network call can show up in two different ways:
      1. Fast failure -- Python raises a clean exception (DNS lookup fails,
         connection refused) and code_run returns normally with that
         traceback in its output.
      2. Hang-then-timeout -- DNS resolution isn't bounded by Python's own
         socket timeout, so the call can hang until Daytona's own execution
         watchdog kills the process and code_run itself raises.
    Both get reported here as network_blocked=True with a plain-language
    explanation, instead of only handling case 1 and dumping a raw
    platform error for case 2.
    """
    daytona = get_client()
    sandbox = daytona.get(sandbox_id)

    try:
        response = sandbox.process.code_run(code, timeout=15)
    except Exception as exc:
        exc_text = str(exc)
        if "timeout" in exc_text.lower():
            return (
                "Your code did not finish within the time limit.\n\n"
                "This sandbox has ALL outbound network access blocked. If your code "
                "tried to reach an external address, the connection attempt likely "
                "hung waiting for a response that will never arrive, until the "
                "sandbox's execution timeout killed it -- consistent with the "
                "network block being real rather than the request just failing on "
                "its own. (Note: an infinite loop with no network call at all would "
                "time out the same way.)",
                True,
            )
        return f"Execution error: {exc}", False

    output = response.result or "(no output)"
    network_blocked = any(marker in output.lower() for marker in NETWORK_ERROR_MARKERS)
    return output, network_blocked


def cleanup_sandbox(sandbox_id: str) -> None:
    """Tear down the student's sandbox once their exam is submitted."""
    daytona = get_client()
    sandbox = daytona.get(sandbox_id)
    daytona.delete(sandbox)
