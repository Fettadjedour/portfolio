// ===== SCROLL REVEAL =====
document.querySelectorAll('.section,.proj-card,.skill-card,.xp,.arch-card,.feat-card,.chart-card,.sira-kpi-card,.vkpi,.ps-block').forEach(el => el.classList.add('reveal'));
const obs = new IntersectionObserver((entries) => {
  entries.forEach((e, i) => { if (e.isIntersecting) { setTimeout(() => e.target.classList.add('visible'), i * 50); obs.unobserve(e.target); } });
}, { threshold: 0.07 });
document.querySelectorAll('.reveal').forEach(el => obs.observe(el));

// ===== COUNTER KPIs =====
function counter(el, target, dur = 1400) {
  let v = 0; const step = target / (dur / 16);
  const t = setInterval(() => { v += step; if (v >= target) { el.textContent = target; clearInterval(t); } else el.textContent = Math.floor(v); }, 16);
}
const heroObs = new IntersectionObserver(entries => {
  if (entries[0].isIntersecting) {
    document.querySelectorAll('.kpi-n[data-target]').forEach(el => counter(el, +el.dataset.target));
    heroObs.disconnect();
  }
}, { threshold: 0.3 });
const heroKpis = document.querySelector('.hero-kpis');
if (heroKpis) heroObs.observe(heroKpis);

// Chart defaults — dark theme
Chart.defaults.color = '#5A6480';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = 'Space Grotesk, sans-serif';

// ===== HERO BG CHART =====
const hc = document.getElementById('heroChart');
if (hc) {
  new Chart(hc, {
    type: 'line',
    data: {
      labels: ['','','','','','','','',''],
      datasets: [
        { data: [30,42,38,58,55,72,68,82,85], borderColor: 'rgba(59,130,246,0.6)', backgroundColor: 'rgba(59,130,246,0.05)', borderWidth: 2, fill: true, tension: 0.45, pointRadius: 0 },
        { data: [20,28,35,40,52,48,60,68,76], borderColor: 'rgba(124,58,237,0.4)', backgroundColor: 'transparent', borderWidth: 1.5, fill: false, tension: 0.45, pointRadius: 0, borderDash: [4,4] }
      ]
    },
    options: { responsive: true, plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { x: { display: false }, y: { display: false } }, animation: { duration: 2200 } }
  });
}

// ===== SIRA MINI CHART =====
const sc = document.getElementById('siraChart');
if (sc) {
  new Chart(sc, {
    type: 'bar',
    data: {
      labels: ['S1','S2','S3','S4','S5','S6','S7','S8'],
      datasets: [
        { label: 'Créés', data: [8,12,6,14,10,8,11,9], backgroundColor: 'rgba(37,99,235,0.5)', borderRadius: 3, borderSkipped: false },
        { label: 'Résolus', data: [6,10,6,12,11,9,10,12], backgroundColor: 'rgba(16,185,129,0.5)', borderRadius: 3, borderSkipped: false }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { font: { size: 11 }, boxWidth: 10, padding: 12 } } },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 10 } } }
      },
      animation: { duration: 1000 }
    }
  });
}

// ===== BAR CHART =====
const bc = document.getElementById('barChart');
if (bc) {
  new Chart(bc, {
    type: 'bar',
    data: {
      labels: ['Triage', 'Recherche historique', 'Rédaction réponse', 'Mise à jour Jira', 'Reporting'],
      datasets: [
        { label: 'Avant SIRA', data: [25,40,30,15,20], backgroundColor: 'rgba(90,100,128,0.3)', borderColor: 'rgba(90,100,128,0.5)', borderWidth: 1, borderRadius: 4 },
        { label: 'Avec SIRA', data: [5,8,10,2,3], backgroundColor: 'rgba(37,99,235,0.7)', borderColor: 'rgba(59,130,246,0.9)', borderWidth: 1, borderRadius: 4 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { font: { size: 12 }, boxWidth: 12, padding: 16 } }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 11 }, callback: v => v + ' min' } }
      },
      animation: { duration: 1200 }
    }
  });
}

// ===== PIE CHART =====
const pc = document.getElementById('pieChart');
if (pc) {
  new Chart(pc, {
    type: 'doughnut',
    data: {
      labels: ['Hébergement VPS (17€)', 'OpenAI Embeddings (~5€)', 'PostgreSQL (0€)', 'Jira (0€)'],
      datasets: [{
        data: [17, 5, 0.1, 0.1],
        backgroundColor: ['rgba(37,99,235,0.75)', 'rgba(124,58,237,0.7)', 'rgba(90,100,128,0.4)', 'rgba(16,185,129,0.4)'],
        borderColor: '#141929', borderWidth: 3, hoverOffset: 6
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '65%',
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 10, padding: 12 } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}` } }
      },
      animation: { duration: 1200, animateRotate: true }
    }
  });
}

// ===== NAV ACTIVE =====
const secs = document.querySelectorAll('section[id]');
const navAs = document.querySelectorAll('.nav-links a');
window.addEventListener('scroll', () => {
  let cur = '';
  secs.forEach(s => { if (window.scrollY >= s.offsetTop - 80) cur = s.id; });
  navAs.forEach(a => { a.style.color = a.getAttribute('href') === '#' + cur ? 'var(--ink)' : ''; });
}, { passive: true });

// ===== ANIMATE PROGRESS BARS =====
const progObs = new IntersectionObserver(entries => {
  if (entries[0].isIntersecting) {
    document.querySelectorAll('.prog-fill').forEach(bar => {
      const w = bar.style.width; bar.style.width = '0';
      setTimeout(() => { bar.style.width = w; }, 100);
    });
    progObs.disconnect();
  }
}, { threshold: 0.3 });
const progBlock = document.querySelector('.voy-progress-block');
if (progBlock) progObs.observe(progBlock);
