import './student.css';

const API = 'https://vtu-project.onrender.com'; // Adjust for your deployment

// ── App Shell ──
document.querySelector('#student-app').innerHTML = `
  <header class="header">
    <h1>VTU Results</h1>
    <p>Verify your marks and GPA instantly</p>
  </header>

  <div class="search-container">
    <form id="search-form" class="search-box">
      <svg class="search-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <input type="text" id="usn-input" class="search-input" placeholder="Enter your USN (e.g. 1RF22CS001)" required maxlength="12" autocomplete="off" spellcheck="false">
      <button type="submit" class="search-btn">Search</button>
    </form>
    <div id="error-msg" class="error-msg"></div>
  </div>

  <div id="spinner" class="spinner-container">
    <div class="spinner"></div>
  </div>

  <div id="result-container" class="result-container">
    <div class="profile-card" id="profile-card"></div>
    <div class="semesters-nav" id="semesters-nav"></div>
    <div class="marks-section" id="marks-section"></div>
  </div>
`;

let currentStudentData = null;

document.getElementById('search-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const usn = document.getElementById('usn-input').value.trim().toUpperCase();
  if (!usn) return;

  const resultContainer = document.getElementById('result-container');
  const errorMsg = document.getElementById('error-msg');
  const spinner = document.getElementById('spinner');

  resultContainer.classList.remove('active');
  errorMsg.classList.remove('active');
  spinner.classList.add('active');

  try {
    const res = await fetch(`${API}/api/results/${usn}`);
    if (!res.ok) {
      throw new Error('Student not found or results pending.');
    }
    const data = await res.json();
    currentStudentData = data;
    
    // Auto-detect latest semester or show all
    renderStudent('all');
    
    spinner.classList.remove('active');
    resultContainer.classList.add('active');
  } catch (err) {
    spinner.classList.remove('active');
    errorMsg.textContent = err.message;
    errorMsg.classList.add('active');
  }
});

// Fallback semester extraction
function getSemFromCode(code) {
  for (const ch of code) {
    if (ch >= '0' && ch <= '9') return parseInt(ch);
  }
  return 0;
}

window.filterSem = function(sem) {
  if (!currentStudentData) return;
  renderStudent(sem);
};

function renderStudent(activeSem) {
  const data = currentStudentData;
  const subjects = data.subjects || {};
  
  // Group by semester
  const semGroups = {};
  Object.entries(subjects).forEach(([code, s]) => {
    const sem = s.semester || getSemFromCode(code);
    if (!semGroups[sem]) semGroups[sem] = [];
    semGroups[sem].push({ code, ...s });
  });
  
  const sortedSems = Object.keys(semGroups).sort((a, b) => Number(a) - Number(b));
  
  // Render Profile
  const initials = (data.name || '?').split(' ').map(w => w[0]).join('').slice(0, 2);
  document.getElementById('profile-card').innerHTML = `
    <div class="profile-avatar">${initials}</div>
    <div class="profile-info">
      <div class="profile-name">${data.name || 'Unknown'}</div>
      <div class="profile-usn">${data.usn} &bull; ${sortedSems.length} Semester${sortedSems.length > 1 ? 's' : ''}</div>
    </div>
    <div class="score-cards">
      <div class="score-card">
        <div class="score-val">${data.sgpa || '-'}</div>
        <div class="score-lbl">Latest SGPA</div>
      </div>
      <div class="score-card">
        <div class="score-val">${data.cgpa || '-'}</div>
        <div class="score-lbl">Overall CGPA</div>
      </div>
    </div>
  `;

  // Render Semesters Nav
  document.getElementById('semesters-nav').innerHTML = `
    <button class="sem-btn ${activeSem === 'all' ? 'active' : ''}" onclick="filterSem('all')">All Semesters</button>
    ${sortedSems.map(sem => `
      <button class="sem-btn ${String(activeSem) === String(sem) ? 'active' : ''}" onclick="filterSem('${sem}')">Semester ${sem}</button>
    `).join('')}
  `;

  // Filter for display
  const semsToShow = activeSem === 'all' ? sortedSems : [String(activeSem)];
  
  // Render Marks
  let marksHtml = '';
  
  semsToShow.forEach(sem => {
    const subs = semGroups[sem].sort((a, b) => a.code.localeCompare(b.code));
    const semTotal = subs.reduce((sum, s) => sum + (s.total || 0), 0);
    const passed = subs.filter(s => s.status === 'P').length;
    
    marksHtml += `
      <div class="marks-container">
        <div class="marks-header">
          <div class="marks-title">Semester ${sem} Marks</div>
          <div class="marks-stats">
            <span>${semTotal}</span> Total Marks &bull; 
            <span>${passed}/${subs.length}</span> Passed &bull; 
            SGPA: <span>${data.sgpa_map && data.sgpa_map[sem] ? Number(data.sgpa_map[sem]).toFixed(2) : '-'}</span>
          </div>
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Subject</th>
                <th>Cr.</th>
                <th>INT</th>
                <th>EXT</th>
                <th>Total</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              ${subs.map(s => `
                <tr>
                  <td class="subject-code">${s.code}</td>
                  <td class="subject-name">${s.name}</td>
                  <td class="mark-val">${s.credits}</td>
                  <td class="mark-val">${s.internals}</td>
                  <td class="mark-val">${s.externals}</td>
                  <td class="mark-total">${s.total}</td>
                  <td>
                    <span class="status-badge ${s.status === 'P' ? 'status-p' : 'status-f'}">
                      ${s.status === 'P' ? 'PASS' : 'FAIL'}
                    </span>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  });
  
  document.getElementById('marks-section').innerHTML = marksHtml;
}
