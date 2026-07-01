import './style.css';

const API = 'https://vtu-project.onrender.com';  // Vite proxy handles /api -> localhost:8000

// ── State ──
let currentJobId = null;
let pollInterval = null;
let allResults = [];

// ── App Shell ──
document.querySelector('#app').innerHTML = `
  <div class="bg-orb bg-orb-1"></div>
  <div class="bg-orb bg-orb-2"></div>
  <div class="bg-orb bg-orb-3"></div>

  <header class="header">
    <div class="header-content">
      <div class="logo">
        <div class="logo-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 1.1.9 2 2 2h8a2 2 0 002-2v-5"/></svg>
        </div>
        <div><div class="logo-text">VTU Scraper</div><div class="logo-sub">Automated Result Extraction</div></div>
      </div>
      <nav class="nav">
        <button class="nav-btn active" data-tab="scrape">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/><path d="M21 3v6h-6"/></svg>
          Scrape
        </button>
        <button class="nav-btn" data-tab="results">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 3v18"/></svg>
          Results
        </button>
        <button class="nav-btn" data-tab="find">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          Find
        </button>
        <button class="nav-btn" data-tab="leaderboard">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          Best
        </button>
      </nav>
      <div class="stat-chip"><span class="stat-dot"></span><span id="stat-count">0</span> Students</div>
    </div>
  </header>

  <main class="main-content">
    <!-- SCRAPE TAB -->
    <section class="tab-content active" id="tab-scrape">
      <div class="section-header">
        <h2 class="section-title">Scrape Results</h2>
        <p class="section-desc">Paste the VTU result URL and configure USN range to start automated scraping.</p>
      </div>
      <div class="cards-grid">
        <div class="card card-wide">
          <div class="card-header">
            <div class="card-icon"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg></div>
            <h3>VTU Result URL</h3>
          </div>
          <div class="input-group">
            <input type="url" id="input-url" class="input" placeholder="https://results.vtu.ac.in/D25J26Ecbcs/index.php">
            <span class="input-label">Paste the VTU result page link</span>
          </div>
        </div>
        <div class="card">
          <div class="card-header">
            <div class="card-icon icon-purple"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/></svg></div>
            <h3>USN Pattern</h3>
          </div>
          <div class="usn-preview">
            <span class="usn-part" id="preview-college">___</span>
            <span class="usn-part" id="preview-year">__</span>
            <span class="usn-part" id="preview-branch">__</span>
            <span class="usn-part highlight" id="preview-roll">001</span>
          </div>
          <div class="input-row">
            <div class="input-group small"><input type="text" id="input-college" class="input" placeholder="1RF" maxlength="4"><span class="input-label">College Code</span></div>
            <div class="input-group small"><input type="text" id="input-year" class="input" placeholder="23" maxlength="2"><span class="input-label">Year</span></div>
            <div class="input-group small"><input type="text" id="input-branch" class="input" placeholder="CS" maxlength="4"><span class="input-label">Branch</span></div>
          </div>
        </div>
        <div class="card">
          <div class="card-header">
            <div class="card-icon icon-cyan"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></svg></div>
            <h3>Roll Number Range</h3>
          </div>
          <div class="input-row">
            <div class="input-group small"><input type="number" id="input-start" class="input" placeholder="1" min="1"><span class="input-label">From</span></div>
            <span class="range-arrow">&rarr;</span>
            <div class="input-group small"><input type="number" id="input-end" class="input" placeholder="200" min="1"><span class="input-label">To</span></div>
          </div>
          <div class="student-count" id="student-count">0 students</div>
          <div class="toggle-row">
            <label class="toggle"><input type="checkbox" id="input-reval"><span class="toggle-slider"></span></label>
            <div class="toggle-label"><span>Revaluation Mode</span><small>Compare &amp; update only improved marks</small></div>
          </div>
        </div>
      </div>
      <div class="action-bar">
        <button class="btn btn-primary btn-large" id="btn-start">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21"/></svg>
          Start Scraping
        </button>
      </div>
      <div class="progress-section hidden" id="progress-section">
        <div class="card card-wide progress-card">
          <div class="progress-header">
            <h3 id="progress-title">Scraping in Progress...</h3>
            <span class="badge badge-running" id="progress-badge">Running</span>
          </div>
          <div class="progress-bar-container"><div class="progress-bar" id="progress-bar"></div></div>
          <div class="progress-stats">
            <div class="progress-stat"><span class="progress-label">Progress</span><span class="progress-value" id="progress-text">0 / 0</span></div>
            <div class="progress-stat"><span class="progress-label">Current USN</span><span class="progress-value" id="progress-usn">-</span></div>
            <div class="progress-stat"><span class="progress-label">Status</span><span class="progress-value" id="progress-status">-</span></div>
            <div class="progress-stat"><span class="progress-label">Elapsed</span><span class="progress-value" id="progress-elapsed">0s</span></div>
          </div>
          <div class="live-log"><div class="log-header">Live Log</div><div class="log-entries" id="log-entries"></div></div>
          <div class="completion-summary hidden" id="completion-summary">
            <div class="summary-grid">
              <div class="summary-item success"><span class="summary-number" id="sum-success">0</span><span class="summary-label" id="sum-success-label">Success</span></div>
              <div class="summary-item failed"><span class="summary-number" id="sum-failed">0</span><span class="summary-label">Failed</span></div>
              <div class="summary-item not-found"><span class="summary-number" id="sum-notfound">0</span><span class="summary-label">Not Found</span></div>
              <div class="summary-item unchanged hidden" id="sum-unchanged-item"><span class="summary-number" id="sum-unchanged">0</span><span class="summary-label">Unchanged</span></div>
              <div class="summary-item time"><span class="summary-number" id="sum-time">0s</span><span class="summary-label">Time</span></div>
            </div>
            <button class="btn btn-success" id="btn-download">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Download Excel Report
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- RESULTS TAB -->
    <section class="tab-content" id="tab-results">
      <div class="section-header"><h2 class="section-title">All Results</h2><p class="section-desc">View all scraped student results from the database.</p></div>
      <div class="results-toolbar">
        <div class="search-box">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" id="results-search" class="search-input" placeholder="Search by USN or name...">
        </div>
        <button class="btn btn-outline" id="btn-refresh">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/><path d="M21 3v6h-6"/></svg>
          Refresh
        </button>
        <div class="export-dropdown" id="export-dropdown">
          <button class="btn btn-success" id="btn-export-toggle">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Export
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
          <div class="export-menu hidden" id="export-menu">
            <button class="export-option" data-sem="all">All Semesters</button>
          </div>
        </div>
      </div>
      <div id="results-area">
        <div class="empty-state" id="results-empty">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 3v18"/></svg>
          <h3>No Results Yet</h3>
          <p>Start a scraping job to see results here.</p>
        </div>
        <table class="results-table hidden" id="results-table">
          <thead><tr><th>#</th><th>USN</th><th>Name</th><th>Subjects</th><th>Passed</th><th>Failed</th><th>Total</th><th>SGPA</th><th>CGPA</th><th>Status</th><th></th></tr></thead>
          <tbody id="results-tbody"></tbody>
        </table>
      </div>
    </section>

    <!-- FIND TAB -->
    <section class="tab-content" id="tab-find">
      <div class="section-header"><h2 class="section-title">Find Student</h2><p class="section-desc">Search for a specific student by USN to view detailed marks.</p></div>
      <div class="find-search-area">
        <div class="find-input-wrapper">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" id="find-usn" class="find-input" placeholder="Enter USN (e.g., 1RF22CS024)" maxlength="12">
          <button class="btn btn-primary" id="btn-find">Search</button>
        </div>
      </div>
      <div id="student-card" class="student-card hidden"></div>
      <div id="find-empty" class="find-empty">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <p>Enter a USN above to find a student's results</p>
      </div>
      <div id="find-error" class="find-error hidden">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        <p id="find-error-msg">Student not found</p>
      </div>
    </section>

    <!-- BEST / LEADERBOARD TAB -->
    <section class="tab-content" id="tab-leaderboard">
      <div class="section-header">
        <h2 class="section-title">Top Performers</h2>
        <p class="section-desc">The absolute best students ranked by their CGPA across all semesters.</p>
      </div>
      <div id="leaderboard-area">
        <div class="leaderboard-grid" id="leaderboard-grid"></div>
      </div>
    </section>
  </main>
`;

// ── Tab Navigation ──
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    if (btn.dataset.tab === 'results' || btn.dataset.tab === 'leaderboard') {
      if (allResults.length === 0) loadAllResults();
      else if (btn.dataset.tab === 'leaderboard') renderLeaderboard();
      else renderResults(allResults);
    }
  });
});

// ── USN Preview ──
const usnInputs = ['input-college', 'input-year', 'input-branch'];
usnInputs.forEach(id => {
  document.getElementById(id).addEventListener('input', () => {
    document.getElementById('preview-college').textContent = document.getElementById('input-college').value.toUpperCase() || '___';
    document.getElementById('preview-year').textContent = document.getElementById('input-year').value || '__';
    document.getElementById('preview-branch').textContent = document.getElementById('input-branch').value.toUpperCase() || '__';
  });
});

// ── Student Count ──
['input-start', 'input-end'].forEach(id => {
  document.getElementById(id).addEventListener('input', () => {
    const s = parseInt(document.getElementById('input-start').value) || 0;
    const e = parseInt(document.getElementById('input-end').value) || 0;
    const count = e >= s && s > 0 ? e - s + 1 : 0;
    document.getElementById('student-count').textContent = `${count} students`;
  });
});

// ── Start Scraping ──
document.getElementById('btn-start').addEventListener('click', async () => {
  const url = document.getElementById('input-url').value.trim();
  const college = document.getElementById('input-college').value.trim().toUpperCase();
  const year = document.getElementById('input-year').value.trim();
  const branch = document.getElementById('input-branch').value.trim().toUpperCase();
  const start = parseInt(document.getElementById('input-start').value);
  const end = parseInt(document.getElementById('input-end').value);
  const isReval = document.getElementById('input-reval').checked;

  if (!url || !college || !year || !branch || !start || !end) {
    alert('Please fill in all fields.'); return;
  }
  if (end < start) { alert('End roll must be >= start roll.'); return; }

  document.getElementById('btn-start').disabled = true;
  document.getElementById('progress-section').classList.remove('hidden');
  document.getElementById('completion-summary').classList.add('hidden');
  document.getElementById('log-entries').innerHTML = '';
  document.getElementById('progress-bar').style.width = '0%';
  document.getElementById('progress-title').textContent = 'Scraping in Progress...';
  document.getElementById('progress-badge').className = 'badge badge-running';
  document.getElementById('progress-badge').textContent = 'Running';
  window._scrapeStartTime = Date.now();

  try {
    const res = await fetch(`${API}/api/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, college_code: college, year, branch, start_roll: start, end_roll: end, is_reval: isReval })
    });
    const data = await res.json();
    currentJobId = data.job_id;
    pollInterval = setInterval(pollStatus, 1500);
  } catch (err) {
    alert('Failed to start scraping: ' + err.message);
    document.getElementById('btn-start').disabled = false;
  }
});

// ── Poll Status ──
let lastLogCount = 0;
async function pollStatus() {
  if (!currentJobId) return;
  try {
    const res = await fetch(`${API}/api/status/${currentJobId}`);
    const data = await res.json();
    const pct = data.percentage || 0;

    document.getElementById('progress-bar').style.width = `${pct}%`;
    document.getElementById('progress-text').textContent = `${data.progress} / ${data.total}`;
    document.getElementById('progress-usn').textContent = data.current_usn || '-';
    document.getElementById('progress-status').textContent = data.current_status || '-';

    // Update elapsed time
    if (window._scrapeStartTime) {
      const elapsed = Math.round((Date.now() - window._scrapeStartTime) / 1000);
      const mins = Math.floor(elapsed / 60);
      const secs = elapsed % 60;
      document.getElementById('progress-elapsed').textContent = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
    }

    // Update live log
    const logEl = document.getElementById('log-entries');
    if (data.results_log && data.results_log.length > 0) {
      const statusLabels = {
        success: '✓ SAVED',
        updated: '↑ UPDATED',
        failed: '✗ FAILED',
        not_found: '⚠ INVALID/NOT FOUND',
        unchanged: '– UNCHANGED'
      };
      const newEntries = data.results_log;
      logEl.innerHTML = newEntries.map(e => {
        const label = statusLabels[e.status] || e.status.toUpperCase();
        const css = e.status === 'updated' ? 'success' : e.status;
        return `<div class="log-entry-${css}">[${label}] ${e.usn}</div>`;
      }).join('');
      logEl.scrollTop = logEl.scrollHeight;
    }

    if (data.status === 'completed' || data.status === 'error') {
      clearInterval(pollInterval);
      pollInterval = null;
      document.getElementById('btn-start').disabled = false;

      if (data.status === 'completed') {
        document.getElementById('progress-title').textContent = 'Scraping Complete!';
        document.getElementById('progress-badge').className = 'badge badge-completed';
        document.getElementById('progress-badge').textContent = 'Completed';
        document.getElementById('progress-bar').style.width = '100%';
        document.getElementById('completion-summary').classList.remove('hidden');

        const s = data.summary || {};
        document.getElementById('sum-success').textContent = s.success_count || 0;
        document.getElementById('sum-failed').textContent = s.failed_count || 0;
        document.getElementById('sum-notfound').textContent = s.not_found_count || 0;
        const secs = Math.round(s.elapsed_seconds || 0);
        document.getElementById('sum-time').textContent = secs > 60 ? `${Math.round(secs/60)}m` : `${secs}s`;

        // Show unchanged count for reval mode
        const unchangedCount = s.unchanged_count || 0;
        const unchangedItem = document.getElementById('sum-unchanged-item');
        if (unchangedCount > 0) {
          unchangedItem.classList.remove('hidden');
          document.getElementById('sum-unchanged').textContent = unchangedCount;
        } else {
          unchangedItem.classList.add('hidden');
        }

        // Update success label for reval mode
        const isRevalMode = document.getElementById('input-reval').checked;
        document.getElementById('sum-success-label').textContent = isRevalMode ? 'Updated' : 'Success';

        updateStatCount();
      } else {
        document.getElementById('progress-title').textContent = 'Scraping Failed';
        document.getElementById('progress-badge').className = 'badge badge-error';
        document.getElementById('progress-badge').textContent = 'Error';
      }
    }
  } catch (err) { console.error('Poll error:', err); }
}

// ── Download Excel ──
document.getElementById('btn-download').addEventListener('click', () => {
  if (currentJobId) window.open(`${API}/api/export/${currentJobId}`, '_blank');
});

// ── Load All Results ──
async function loadAllResults() {
  try {
    const res = await fetch(`${API}/api/results`);
    const data = await res.json();
    allResults = data.results || [];
    if (document.querySelector('[data-tab="results"]').classList.contains('active')) {
      renderResults(allResults);
    } else if (document.querySelector('[data-tab="leaderboard"]').classList.contains('active')) {
      renderLeaderboard();
    }
    updateStatCount();
  } catch (err) { console.error('Load results error:', err); }
}

function renderLeaderboard() {
  const grid = document.getElementById('leaderboard-grid');
  const sorted = [...allResults].filter(r => r.cgpa > 0).sort((a, b) => b.cgpa - a.cgpa);
  
  if (sorted.length === 0) {
    grid.innerHTML = '<div class="empty-state"><h3>No CGPA data available yet</h3></div>';
    return;
  }
  
  const top10 = sorted.slice(0, 10);
  
  grid.innerHTML = top10.map((r, i) => {
    let rankClass = 'default';
    if (i === 0) rankClass = 'gold';
    else if (i === 1) rankClass = 'silver';
    else if (i === 2) rankClass = 'bronze';
    
    return `
      <div class="leaderboard-card" onclick="viewStudent('${r.usn}')">
        <div class="rank-badge ${rankClass}">#${i+1}</div>
        <div class="lb-info">
          <div class="lb-name">${r.name || 'Unknown'}</div>
          <div class="lb-usn">${r.usn}</div>
        </div>
        <div class="lb-score">
          <span class="lb-cgpa">${r.cgpa.toFixed(2)}</span>
          <span class="lb-label">CGPA</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderResults(results) {
  const tbody = document.getElementById('results-tbody');
  const table = document.getElementById('results-table');
  const empty = document.getElementById('results-empty');

  if (!results.length) {
    table.classList.add('hidden');
    empty.classList.remove('hidden');
    return;
  }
  table.classList.remove('hidden');
  empty.classList.add('hidden');

  const sorted = [...results].sort((a, b) => (a.usn || '').localeCompare(b.usn || ''));
  tbody.innerHTML = sorted.map((r, i) => {
    const subs = r.subjects ? Object.keys(r.subjects).length : 0;
    const passed = r.subjects ? Object.values(r.subjects).filter(s => s.status === 'P').length : 0;
    const failed = subs - passed;
    const overall = failed === 0 && subs > 0 ? 'PASS' : 'FAIL';
    return `<tr>
      <td>${i + 1}</td>
      <td style="font-family:'Courier New',monospace;font-weight:600">${r.usn}</td>
      <td>${r.name || '-'}</td>
      <td>${subs}</td>
      <td style="color:var(--green)">${passed}</td>
      <td style="color:${failed > 0 ? 'var(--red)' : 'var(--text-muted)'}">${failed}</td>
      <td style="font-weight:700">${r.grand_total || 0}</td>
      <td style="font-weight:700; color:var(--purple)">${r.sgpa || '-'}</td>
      <td style="font-weight:700; color:var(--cyan)">${r.cgpa || '-'}</td>
      <td class="${overall === 'PASS' ? 'status-pass' : 'status-fail'}">${overall}</td>
      <td><button class="btn-view" onclick="viewStudent('${r.usn}')">View</button></td>
    </tr>`;
  }).join('');
}

document.getElementById('results-search').addEventListener('input', (e) => {
  const q = e.target.value.toUpperCase();
  const filtered = allResults.filter(r =>
    (r.usn || '').toUpperCase().includes(q) || (r.name || '').toUpperCase().includes(q)
  );
  renderResults(filtered);
});

document.getElementById('btn-refresh').addEventListener('click', loadAllResults);

// ── Export Dropdown ──
document.getElementById('btn-export-toggle').addEventListener('click', (e) => {
  e.stopPropagation();
  const menu = document.getElementById('export-menu');
  menu.classList.toggle('hidden');
  // Load semesters if not loaded yet
  if (menu.querySelectorAll('.export-option').length <= 1) {
    loadExportSemesters();
  }
});

// Close dropdown on outside click
document.addEventListener('click', () => {
  document.getElementById('export-menu').classList.add('hidden');
});

async function loadExportSemesters() {
  try {
    const res = await fetch(`${API}/api/semesters`);
    const data = await res.json();
    const menu = document.getElementById('export-menu');
    // Keep the 'All' option, add per-sem options
    const semButtons = (data.semesters || []).map(s =>
      `<button class="export-option" data-sem="${s}">Semester ${s}</button>`
    ).join('');
    menu.innerHTML = `<button class="export-option" data-sem="all">All Semesters</button>${semButtons}`;
    // Attach click handlers
    menu.querySelectorAll('.export-option').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const sem = btn.dataset.sem;
        const url = sem === 'all' ? `${API}/api/export` : `${API}/api/export?semester=${sem}`;
        window.open(url, '_blank');
        menu.classList.add('hidden');
      });
    });
  } catch (err) { console.error('Failed to load semesters:', err); }
}

// ── Find Student ──
window.viewStudent = function(usn) {
  document.getElementById('find-usn').value = usn;
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelector('[data-tab="find"]').classList.add('active');
  document.getElementById('tab-find').classList.add('active');
  findStudent(usn);
};

document.getElementById('btn-find').addEventListener('click', () => findStudent());
document.getElementById('find-usn').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') findStudent();
});

// Cache for re-rendering on semester pill clicks
let _lastStudentData = null;

async function findStudent(usnArg) {
  const usn = (usnArg || document.getElementById('find-usn').value).trim().toUpperCase();
  if (!usn) return;

  const card = document.getElementById('student-card');
  const empty = document.getElementById('find-empty');
  const error = document.getElementById('find-error');

  card.classList.add('hidden');
  empty.classList.add('hidden');
  error.classList.add('hidden');

  try {
    const res = await fetch(`${API}/api/results/${usn}`);
    if (!res.ok) {
      error.classList.remove('hidden');
      document.getElementById('find-error-msg').textContent = `No result found for USN: ${usn}`;
      return;
    }
    _lastStudentData = await res.json();
    renderStudentCard(_lastStudentData, 'all');
    card.classList.remove('hidden');
  } catch (err) {
    error.classList.remove('hidden');
    document.getElementById('find-error-msg').textContent = 'Error connecting to server.';
  }
}

// Called when a semester pill is clicked
window.filterSem = function(sem) {
  if (!_lastStudentData) return;
  renderStudentCard(_lastStudentData, sem);
  document.getElementById('student-card').classList.remove('hidden');
};

function renderStudentCard(data, activeSem) {
  const card = document.getElementById('student-card');
  const subjects = data.subjects || {};
  const initials = (data.name || '?').split(' ').map(w => w[0]).join('').slice(0, 2);

  // Group subjects by semester
  const semGroups = {};
  Object.entries(subjects).forEach(([code, s]) => {
    const sem = s.semester || _getSemFromCode(code);
    if (!semGroups[sem]) semGroups[sem] = [];
    semGroups[sem].push({ code, ...s });
  });
  const sortedSems = Object.keys(semGroups).sort((a, b) => Number(a) - Number(b));

  // Build semester pills
  const pills = `
    <div class="sem-pills">
      <button class="sem-pill ${activeSem === 'all' ? 'active' : ''}" onclick="filterSem('all')">All Semesters</button>
      ${sortedSems.map(sem => `
        <button class="sem-pill ${String(activeSem) === String(sem) ? 'active' : ''}" onclick="filterSem('${sem}')">Sem ${sem}</button>
      `).join('')}
    </div>
  `;

  // Filter semesters to show
  const semsToShow = activeSem === 'all' ? sortedSems : sortedSems.filter(s => String(s) === String(activeSem));

  // Compute displayed total
  let displayTotal = 0;
  semsToShow.forEach(sem => {
    semGroups[sem].forEach(s => { displayTotal += s.total || 0; });
  });

  // Build semester sections
  const semSections = semsToShow.map(sem => {
    const subs = semGroups[sem].sort((a, b) => a.code.localeCompare(b.code));
    const semTotal = subs.reduce((sum, s) => sum + (s.total || 0), 0);
    const semPassed = subs.filter(s => s.status === 'P').length;
    const semFailed = subs.length - semPassed;
    const hasReval = subs.some(s => s.old_marks !== undefined || s.rv_marks !== undefined);

    const headers = hasReval
      ? '<th>Code</th><th>Subject Name</th><th>Cr.</th><th>Internal</th><th>Old Total</th><th>RV Total</th><th>New Total</th><th>Result</th>'
      : '<th>Code</th><th>Subject Name</th><th>Cr.</th><th>Internal</th><th>External</th><th>Total</th><th>Result</th>';

    return `
      <div class="sem-section">
        <div class="sem-header">
          <span class="sem-badge">Semester ${sem}${hasReval ? ' <span class="reval-tag">REVAL</span>' : ''}</span>
          <span class="sem-stats">${subs.length} subjects &middot; Total: ${semTotal} &middot; <span style="color:var(--green)">${semPassed}P</span>${semFailed > 0 ? ` <span style="color:var(--red)">${semFailed}F</span>` : ''} &middot; <span style="color:var(--purple); font-weight:700;">SGPA: ${data.sgpa_map && data.sgpa_map[sem] !== undefined ? Number(data.sgpa_map[sem]).toFixed(2) : '-'}</span></span>
        </div>
        <table class="marks-table">
          <thead><tr>${headers}</tr></thead>
          <tbody>
            ${subs.map(s => {
              if (hasReval) {
                const oldTotal = s.old_total ?? (s.old_marks !== undefined ? s.internals + s.old_marks : '-');
                const rvTotal = s.rv_total ?? (s.rv_marks !== undefined ? s.internals + s.rv_marks : '-');
                const improved = typeof oldTotal === 'number' && s.total > oldTotal;
                return `
                <tr${improved ? ' class="reval-improved"' : ''}>
                  <td style="font-family:'Courier New',monospace;font-weight:600">${s.code}</td>
                  <td>${s.name}</td>
                  <td style="font-weight:600; text-align:center">${s.credits}</td>
                  <td>${s.internals}</td>
                  <td style="color:var(--text-muted)">${oldTotal}</td>
                  <td style="color:var(--cyan)">${rvTotal}</td>
                  <td style="font-weight:700">${s.total}${improved ? ' <span style="color:var(--green)">↑</span>' : ''}</td>
                  <td class="${s.status === 'P' ? 'result-pass' : 'result-fail'}">${s.status === 'P' ? 'PASS' : 'FAIL'}</td>
                </tr>`;
              }
              return `
              <tr>
                <td style="font-family:'Courier New',monospace;font-weight:600">${s.code}</td>
                <td>${s.name}</td>
                <td style="font-weight:600; text-align:center">${s.credits}</td>
                <td>${s.internals}</td>
                <td>${s.externals}</td>
                <td style="font-weight:700">${s.total}</td>
                <td class="${s.status === 'P' ? 'result-pass' : 'result-fail'}">${s.status === 'P' ? 'PASS' : 'FAIL'}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }).join('');

  const totalLabel = activeSem === 'all' ? 'Grand Total' : `Sem ${activeSem} Total`;

  card.innerHTML = `
    <div class="student-header">
      <div class="student-avatar">${initials}</div>
      <div class="student-info">
        <div class="student-name">${data.name || 'Unknown'}</div>
        <div class="student-usn">${data.usn} &middot; ${sortedSems.length} semester${sortedSems.length > 1 ? 's' : ''} on record</div>
      </div>
      <div class="student-total" style="padding: 10px 16px; border-radius: var(--radius-sm); background: rgba(139, 92, 246, 0.08); border: 1px solid rgba(139, 92, 246, 0.2);">
        <span class="total-number" style="color: var(--purple); font-size: 28px;">${data.sgpa || '-'}</span>
        <span class="total-label" style="color: var(--purple)">Latest SGPA</span>
      </div>
      <div class="student-total" style="padding: 10px 16px; border-radius: var(--radius-sm); background: rgba(34, 211, 238, 0.08); border: 1px solid rgba(34, 211, 238, 0.2);">
        <span class="total-number" style="color: var(--cyan); font-size: 28px;">${data.cgpa || '-'}</span>
        <span class="total-label" style="color: var(--cyan)">CGPA</span>
      </div>
      <div class="student-total">
        <span class="total-number">${displayTotal}</span>
        <span class="total-label">${totalLabel}</span>
      </div>
    </div>
    ${pills}
    <div class="marks-table-wrapper">
      ${semSections}
    </div>
  `;
}

// Fallback semester extraction if backend doesn't have it yet
function _getSemFromCode(code) {
  for (const ch of code) {
    if (ch >= '0' && ch <= '9') return parseInt(ch);
  }
  return 0;
}

// ── Stats ──
async function updateStatCount() {
  try {
    const res = await fetch(`${API}/api/stats`);
    const data = await res.json();
    document.getElementById('stat-count').textContent = data.total_students || 0;
  } catch (err) { /* ignore */ }
}

// ── Init ──
updateStatCount();
