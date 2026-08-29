(function () {
  const tbody = document.getElementById('dashboard-body');
  const overlay = document.getElementById('report-overlay');
  const content = document.getElementById('report-content');
  const closeBtn = document.getElementById('close-report');

  function render(sessions) {
    tbody.innerHTML = '';
    sessions.forEach((s) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHtml(s.student_name)}</td>
        <td>${escapeHtml(s.student_id)}</td>
        <td><span class="badge ${s.sandbox_status}">${s.sandbox_status}</span></td>
        <td>${s.status}</td>
        <td>${s.flag_count}</td>
        <td><span class="badge ${s.risk_verdict}">${s.risk_verdict} (${s.risk_score})</span></td>
        <td><button data-id="${s.id}" class="view-btn" type="button">View</button></td>
      `;
      tbody.appendChild(tr);
    });
    document.querySelectorAll('.view-btn').forEach((btn) => {
      btn.addEventListener('click', () => openReport(btn.dataset.id));
    });
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function openReport(id) {
    fetch(`/api/dashboard/session/${id}`)
      .then((r) => r.json())
      .then((data) => {
        const { session, answers, flags, questions } = data;
        const answerMap = Object.fromEntries(answers.map((a) => [String(a.question_id), a.answer]));
        const qHtml = questions
          .map(
            (q) =>
              `<div class="report-q"><strong>${escapeHtml(q.text)}</strong><p>${
                escapeHtml(answerMap[String(q.id)] || '') || '<em>no answer</em>'
              }</p></div>`
          )
          .join('');
        const flagHtml = flags.length
          ? flags.map((f) => `<li>[${f.ts}] ${escapeHtml(f.type)} ${escapeHtml(f.detail || '')}</li>`).join('')
          : '<li>No flags recorded.</li>';
        content.innerHTML = `
          <h2>${escapeHtml(session.student_name)} (${escapeHtml(session.student_id)})</h2>
          <p>Sandbox: ${escapeHtml(session.sandbox_id || 'n/a')} — ${session.sandbox_status}</p>
          <p>Risk: <strong>${session.risk_verdict}</strong> (${session.risk_score}/100)</p>
          <h3>Answers</h3>
          ${qHtml}
          <h3>Activity Log</h3>
          <ul class="flag-log">${flagHtml}</ul>
        `;
        overlay.classList.remove('hidden');
      });
  }

  closeBtn.addEventListener('click', () => overlay.classList.add('hidden'));

  function refresh() {
    fetch('/api/dashboard')
      .then((r) => r.json())
      .then(render)
      .catch(() => {});
  }

  refresh();
  setInterval(refresh, 3000);
})();
