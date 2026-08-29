(function () {
  const EXAM_DURATION_SECONDS = 20 * 60;
  const IDLE_THRESHOLD_MS = 20000; // 20s, tuned short for live demo purposes

  let remaining = EXAM_DURATION_SECONDS;
  let submitted = false;
  let lastActivity = Date.now();
  let idleFlagged = false;

  const timerEl = document.getElementById('timer');
  const statusEl = document.getElementById('sandbox-status');
  const warningBanner = document.getElementById('warning-banner');
  const submitBtn = document.getElementById('submit-btn');
  const overlay = document.getElementById('submitted-overlay');
  const submittedMsg = document.getElementById('submitted-msg');
  const form = document.getElementById('exam-form');

  function showWarning(text) {
    warningBanner.textContent = text;
    warningBanner.classList.remove('hidden');
    setTimeout(() => warningBanner.classList.add('hidden'), 4000);
  }

  function sendFlag(type, detail) {
    showWarning(`⚠ Flagged: ${type.replace('_', ' ')}`);
    fetch('/api/flag', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type, detail: detail || '' }),
    }).catch(() => {});
  }

  function startSandbox() {
    fetch('/api/exam/start', { method: 'POST' })
      .then((r) => r.json())
      .then((data) => {
        if (data.status === 'active') {
          statusEl.textContent = `Sandbox: active (${data.sandbox_id.slice(0, 8)}…)`;
          statusEl.className = 'badge active';
        } else {
          statusEl.textContent = 'Sandbox: unavailable (fallback mode)';
          statusEl.className = 'badge error';
        }
      })
      .catch(() => {
        statusEl.textContent = 'Sandbox: unavailable (fallback mode)';
        statusEl.className = 'badge error';
      });
  }

  function saveAnswer(questionId, value) {
    fetch('/api/exam/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: Number(questionId), answer: value }),
    }).catch(() => {});
  }

  function formatTime(s) {
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  }

  function tick() {
    if (submitted) return;
    remaining -= 1;
    timerEl.textContent = formatTime(Math.max(remaining, 0));
    if (remaining <= 0) submitExam();
  }

  function submitExam() {
    if (submitted) return;
    submitted = true;
    submitBtn.disabled = true;
    fetch('/api/exam/submit', { method: 'POST' })
      .then((r) => r.json())
      .then((data) => {
        submittedMsg.textContent =
          `Your exam has been submitted and your sandbox has been securely torn down. ` +
          `(Internal integrity score: ${data.risk_score}/100 — ${data.risk_verdict})`;
        overlay.classList.remove('hidden');
      })
      .catch(() => {
        submittedMsg.textContent = 'Your exam has been submitted.';
        overlay.classList.remove('hidden');
      });
  }

  // Autosave answers
  form.querySelectorAll('input, textarea').forEach((el) => {
    el.addEventListener('change', () => {
      const qid = el.closest('.question').dataset.qid;
      const value =
        el.type === 'radio'
          ? (form.querySelector(`input[name="${el.name}"]:checked`) || {}).value
          : el.value;
      saveAnswer(qid, value || '');
    });
  });

  // --- Integrity monitoring ---

  document.addEventListener('visibilitychange', () => {
    if (document.hidden && !submitted) sendFlag('tab_switch');
  });

  ['copy', 'cut', 'paste'].forEach((evt) => {
    document.addEventListener(evt, (e) => {
      if (submitted) return;
      e.preventDefault();
      sendFlag(evt);
    });
  });

  ['mousemove', 'keydown', 'click'].forEach((evt) => {
    document.addEventListener(evt, () => {
      lastActivity = Date.now();
      idleFlagged = false;
    });
  });

  setInterval(() => {
    if (submitted) return;
    if (Date.now() - lastActivity > IDLE_THRESHOLD_MS && !idleFlagged) {
      idleFlagged = true;
      sendFlag('idle', `${Math.round((Date.now() - lastActivity) / 1000)}s idle`);
    }
  }, 5000);

  // Rough devtools-open heuristic (viewport vs window size gap)
  setInterval(() => {
    if (submitted) return;
    const widthDiff = window.outerWidth - window.innerWidth;
    const heightDiff = window.outerHeight - window.innerHeight;
    if (widthDiff > 160 || heightDiff > 160) sendFlag('devtools');
  }, 4000);

  submitBtn.addEventListener('click', submitExam);

  startSandbox();
  setInterval(tick, 1000);
})();
