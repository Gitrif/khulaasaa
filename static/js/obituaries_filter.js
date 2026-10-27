/**
 * Client-side Obituaries & Janaza Notices Filter Controller.
 * Handles regional filtering, atoll selection, instant search matching,
 * and Thaana clipboard notice copying with toast confirmation.
 * Strictly under 500 lines. Zero emojis.
 */

let activeRegion = 'all';
let activeAtoll = 'all';

function filterByRegion(region) {
  activeRegion = region;
  activeAtoll = 'all';
  const atollSelect = document.getElementById('atollSelect');
  if (atollSelect) atollSelect.value = 'all';

  document.querySelectorAll('.filter-pill').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById('btn-reg-' + region);
  if (activeBtn) activeBtn.classList.add('active');

  applyFilters();
}

function filterByAtoll(atoll) {
  activeAtoll = atoll;
  applyFilters();
}

function applyFilters() {
  const searchEl = document.getElementById('obituarySearch');
  const q = (searchEl ? searchEl.value : '').toLowerCase().trim();
  const cards = document.querySelectorAll('.obituary-card');
  let visible = 0;

  cards.forEach(card => {
    const nameDv = (card.getAttribute('data-name-dv') || '').toLowerCase();
    const nameEn = (card.getAttribute('data-name-en') || '').toLowerCase();
    const addrDv = (card.getAttribute('data-address-dv') || '').toLowerCase();
    const addrEn = (card.getAttribute('data-address-en') || '').toLowerCase();
    const mosque = (card.getAttribute('data-mosque') || '').toLowerCase();
    const cardAtoll = card.getAttribute('data-atoll') || '';
    const cardRegion = card.getAttribute('data-region') || '';
    const cardIsland = (card.getAttribute('data-island') || '').toLowerCase();

    const matchQ = !q || nameDv.includes(q) || nameEn.includes(q) || addrDv.includes(q) || addrEn.includes(q) || mosque.includes(q) || cardIsland.includes(q);
    const matchRegion = (activeRegion === 'all' || cardRegion === activeRegion);
    const matchAtoll = (activeAtoll === 'all' || cardAtoll === activeAtoll);

    if (matchQ && matchRegion && matchAtoll) {
      card.style.display = '';
      visible++;
    } else {
      card.style.display = 'none';
    }
  });

  const cnt = document.getElementById('visibleCount');
  if (cnt) cnt.textContent = visible;
}

function copyNotice(name, address, mosque, prayerTime, contacts) {
  const text = `ކަށުނަމާދު:\n${name}\n${address ? address + '\n' : ''}ކަށުނަމާދު އޮންނާނީ: ${prayerTime} ${mosque}ގައި\n${contacts ? 'އާއިލާގެ ނަންބަރު: ' + contacts : ''}`;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      const toast = document.getElementById('copyToast');
      if (toast) {
        toast.style.opacity = '1';
        setTimeout(() => {
          toast.style.opacity = '0';
        }, 2200);
      }
    });
  }
}
