'use strict';

const form = document.getElementById('form');
const problemEl = document.getElementById('problem');
const counterEl = document.getElementById('counter');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');
const submitBtn = document.getElementById('submit');
const sourceEl = document.getElementById('source');

const API_URL = '/api/recommend';

problemEl.addEventListener('input', () => {
  counterEl.textContent = `${problemEl.value.length} / 2000`;
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const problem = problemEl.value.trim();

  if (problem.length < 10) {
    setStatus('Opisz problem szerzej (min. 10 znakow).', 'error');
    return;
  }

  setStatus('Szukam rekomendacji...', 'loading');
  resultsEl.innerHTML = '';
  submitBtn.disabled = true;

  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ problem }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }

    setStatus('', '');
    renderResults(data.recommendations || []);
    if (data.source) {
      sourceEl.textContent = `Zrodlo: ${data.source} · ${data.version || ''}`;
    }
  } catch (err) {
    setStatus('Blad: ' + err.message, 'error');
  } finally {
    submitBtn.disabled = false;
  }
});

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = kind ? `status ${kind}` : '';
}

function renderResults(recs) {
  if (!recs.length) {
    resultsEl.innerHTML = '<p class="empty">Brak rekomendacji.</p>';
    return;
  }
  resultsEl.innerHTML = recs
    .map((r, i) => `
      <article class="rec">
        <h3>${i + 1}. ${escapeHtml(r.name)}</h3>
        <p class="desc">${escapeHtml(r.description)}</p>
        <p class="why"><strong>Dlaczego:</strong> ${escapeHtml(r.why)}</p>
        ${r.url ? `<a href="${escapeHtml(r.url)}" target="_blank" rel="noopener">Otworz strone &rarr;</a>` : ''}
      </article>
    `)
    .join('');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[c]);
}
