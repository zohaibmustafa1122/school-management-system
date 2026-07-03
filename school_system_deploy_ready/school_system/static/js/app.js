// ── MODALS ────────────────────────────────────────────────
function openModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.add('open'); document.body.style.overflow = 'hidden'; }
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.remove('open'); document.body.style.overflow = ''; }
}
document.querySelectorAll('.modal-ov').forEach(el => {
  el.addEventListener('click', e => { if (e.target === el) closeModal(el.id); });
});

// ── TOAST AUTO-DISMISS ────────────────────────────────────
document.querySelectorAll('.toast').forEach(t => {
  setTimeout(() => {
    t.style.transition = 'opacity .4s, transform .4s';
    t.style.opacity = '0'; t.style.transform = 'translateY(-8px)';
    setTimeout(() => t.remove(), 400);
  }, 5000);
});

// ── SIDEBAR MOBILE ────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}
document.addEventListener('click', e => {
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  if (sidebar && !sidebar.contains(e.target) && hamburger && !hamburger.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});

// ── MARKS INPUT VALIDATION ────────────────────────────────
document.querySelectorAll('.marks-input').forEach(input => {
  input.addEventListener('input', function() {
    const totalInput = document.querySelector('input[name="total_marks"]');
    if (totalInput) {
      const total = parseFloat(totalInput.value) || 100;
      const val = parseFloat(this.value);
      if (val > total) { this.value = total; this.style.borderColor = '#f59e0b'; }
      else if (val < 0) { this.value = 0; }
      else { this.style.borderColor = ''; }
    }
  });
});
