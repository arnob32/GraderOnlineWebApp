// student.js — student panel shared JS

const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebar-overlay');
const menuBtn = document.getElementById('menu-toggle');

function openSidebar()  { sidebar?.classList.add('open');    overlay?.classList.add('open'); }
function closeSidebar() { sidebar?.classList.remove('open'); overlay?.classList.remove('open'); }

menuBtn?.addEventListener('click', openSidebar);
overlay?.addEventListener('click', closeSidebar);

// Active nav link
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-item').forEach(link => {
  if (link.getAttribute('href') === currentPath) link.classList.add('active');
});

// Progress bar color based on percentage
function colorProgress(pct) {
  if (pct >= 70) return 'good';
  if (pct >= 50) return 'medium';
  return 'poor';
}