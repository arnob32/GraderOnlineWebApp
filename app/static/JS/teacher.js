function toggleSubject(id, hdr) {
  const body = document.getElementById('body-' + id);
  const icon = document.getElementById('icon-' + id);
  const isOpen = body.classList.contains('open');
  body.classList.toggle('open', !isOpen);
  icon.classList.toggle('open', !isOpen);
}