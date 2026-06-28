// admin.js — admin panel shared JS

// ── Sidebar toggle (mobile) ───────────────────
const sidebar  = document.getElementById('sidebar');
const overlay  = document.getElementById('sidebar-overlay');
const menuBtn  = document.getElementById('menu-toggle');

function openSidebar() {
  sidebar?.classList.add('open');
  overlay?.classList.add('open');
}

function closeSidebar() {
  sidebar?.classList.remove('open');
  overlay?.classList.remove('open');
}

menuBtn?.addEventListener('click', openSidebar);
overlay?.addEventListener('click', closeSidebar);

// ── Active nav link ───────────────────────────
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-item').forEach(link => {
  if (link.getAttribute('href') === currentPath) {
    link.classList.add('active');
  }
});

// ── Confirm delete forms ──────────────────────
document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', (e) => {
    const msg = form.dataset.confirm || 'Are you sure you want to delete this?';
    if (!confirm(msg)) e.preventDefault();
  });
});