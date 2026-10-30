/**
 * Client-side News Feed Search & Card Filter Controller.
 * Strictly under 500 lines. Zero emojis.
 */

function filterCards(query) {
  const q = (query || '').trim().toLowerCase();
  const cards = document.querySelectorAll('.story-card');
  let anyVisible = false;
  cards.forEach(c => {
    const match = !q || (c.dataset.search || '').includes(q);
    c.style.display = match ? '' : 'none';
    if (match) anyVisible = true;
  });
  document.querySelectorAll('.card-stack').forEach(stack => {
    const total = stack.querySelectorAll('.story-card').length;
    const visible = Array.from(stack.querySelectorAll('.story-card')).some(c => c.style.display !== 'none');
    if (total) {
      const sec = stack.closest('section');
      if (sec) sec.style.display = visible ? '' : 'none';
    }
  });
  const noRes = document.getElementById('noResults');
  if (noRes) noRes.style.display = (q && !anyVisible) ? '' : 'none';
}
window.filterCards = filterCards;
