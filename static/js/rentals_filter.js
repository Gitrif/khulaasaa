/**
 * Client-side Rentals & Apartment Filter Controller for Khulaasaa.
 * Manages Atoll/Island/Ward cascading dropdowns, room selectors (BHK),
 * budget range sliders, and multi-attribute property amenity filtering.
 * Strictly under 500 lines. Zero emojis.
 */

const ISLAND_WARDS = {
  'all': [{ label: 'All Wards / Phases', value: '' }],
  'male': [
    { label: 'All Wards', value: '' },
    { label: 'Henveiru', value: 'henveiru' },
    { label: 'Galolhu', value: 'galolhu' },
    { label: 'Machangoalhi', value: 'machangoalhi' },
    { label: 'Maafannu', value: 'maafannu' }
  ],
  'hulhumale': [
    { label: 'All Phases', value: '' },
    { label: 'Phase 1', value: 'phase 1' },
    { label: 'Phase 2', value: 'phase 2' }
  ],
  'villimale': [{ label: 'All Villimale', value: 'villimale' }],
  'other': [{ label: 'All Other Islands', value: '' }]
};

let currentAtoll = 'all';
let currentIsland = 'all';
let currentWard = '';
let currentRooms = 0;
let currentMaxPrice = 0;
const activeLegendFeatures = new Set();
function onAtollChange(atoll) {
  currentAtoll = atoll;
  if (atoll === 'k') {
    onIslandChange('all');
  } else if (atoll === 's' || atoll === 'gn') {
    onIslandChange('other');
  } else {
    onIslandChange('all');
  }
}

function onIslandChange(island) {
  currentIsland = island;
  currentWard = '';
  const el = document.getElementById('filterWard');
  if (el) {
    const list = ISLAND_WARDS[island] || ISLAND_WARDS['all'];
    el.innerHTML = list.map(item => `<option value="${item.value}">${item.label}</option>`).join('');
    el.value = '';
  }
  const islEl = document.getElementById('filterIsland');
  if (islEl && islEl.value !== island) islEl.value = island;
  applyAllCardFilters();
}

function onWardChange(ward) {
  currentWard = ward;
  applyAllCardFilters();
}

function setRoomsFilter(rooms, btn) {
  currentRooms = parseInt(rooms, 10);
  const cust = document.getElementById('filterCustomRooms');
  if (cust) cust.value = '';
  document.querySelectorAll('.bhk-btn').forEach(b => {
    const r = parseInt(b.getAttribute('data-rooms'), 10);
    const isAct = (r === currentRooms) || (r === 5 && currentRooms >= 5);
    b.className = 'bhk-btn filter-pill' + (isAct ? ' active' : '');
  });
  applyAllCardFilters();
}

function setCustomRooms(val) {
  const num = parseInt(val, 10);
  if (!isNaN(num) && num > 0) {
    currentRooms = num;
    document.querySelectorAll('.bhk-btn').forEach(b => b.classList.remove('active'));
    applyAllCardFilters();
  } else if (!val) {
    setRoomsFilter(0);
  }
}

function updateBudgetSlider(val) {
  const num = parseInt(val, 10) || 0;
  const el = document.getElementById('budgetRangeSlider');
  if (el && el.value != num) el.value = num;
  const disp = document.getElementById('budgetScrollerValue');
  const txt = num >= 60000 ? 'Any Rent (Unlimited)' : 'Up to MVR ' + num.toLocaleString() + ' / month';
  if (disp) disp.innerText = txt;
  currentMaxPrice = num >= 60000 ? 0 : num;
  applyAllCardFilters();
}

function resetAllRentalFilters() {
  currentAtoll = 'all';
  currentIsland = 'all';
  currentWard = '';
  currentRooms = 0;
  currentMaxPrice = 0;
  const atollEl = document.getElementById('filterAtoll');
  if (atollEl) atollEl.value = 'all';
  const islEl = document.getElementById('filterIsland');
  if (islEl) islEl.value = 'all';
  onIslandChange('all');
  setRoomsFilter(0);
  updateBudgetSlider(60000);
  clearAllFeatureFilters();
}

function toggleFeatureFilter(feat, btn) {
  const on = activeLegendFeatures.has(feat);
  if (on) {
    activeLegendFeatures.delete(feat);
    btn.style.backgroundColor = 'var(--surface-white)';
    btn.style.borderColor = 'var(--color-border)';
    btn.style.color = 'var(--color-ink)';
    btn.style.fontWeight = '600';
    btn.style.boxShadow = 'none';
    const b = btn.querySelector('.legend-badge');
    if (b) { b.style.backgroundColor = '#ecfdf5'; b.style.borderColor = '#6ee7b7'; const s = b.querySelector('svg'); if (s) s.style.stroke = '#047857'; }
  } else {
    activeLegendFeatures.add(feat);
    btn.style.backgroundColor = 'var(--color-accent)';
    btn.style.borderColor = 'var(--color-accent)';
    btn.style.color = 'var(--surface-white)';
    btn.style.fontWeight = '600';
    btn.style.boxShadow = 'none';
    const b = btn.querySelector('.legend-badge');
    if (b) { b.style.backgroundColor = 'rgba(255,255,255,0.2)'; b.style.borderColor = 'rgba(255,255,255,0.35)'; const s = b.querySelector('svg'); if (s) s.style.stroke = '#ffffff'; }
  }
  applyAllCardFilters();
}

function clearAllFeatureFilters() {
  activeLegendFeatures.clear();
  document.querySelectorAll('.legend-filter-btn').forEach(btn => {
    btn.style.backgroundColor = 'var(--surface-white)';
    btn.style.borderColor = 'var(--color-border)';
    btn.style.color = 'var(--color-ink)';
    btn.style.fontWeight = '600';
    btn.style.boxShadow = 'none';
    const b = btn.querySelector('.legend-badge');
    if (b) { b.style.backgroundColor = '#ecfdf5'; b.style.borderColor = '#6ee7b7'; const s = b.querySelector('svg'); if (s) s.style.stroke = '#047857'; }
  });
  applyAllCardFilters();
}

function applyAllCardFilters() {
  const cards = document.querySelectorAll('[data-card-rental="1"]');
  let vis = 0;
  cards.forEach(card => {
    let match = true;

    // Island
    if (currentIsland !== 'all') {
      const cardIsland = card.getAttribute('data-island') || '';
      if (cardIsland !== currentIsland) match = false;
    }

    // Ward
    if (match && currentWard !== '') {
      const cardWard = (card.getAttribute('data-ward') || '').toLowerCase();
      if (!cardWard.includes(currentWard.toLowerCase())) match = false;
    }

    // Rooms
    if (match && currentRooms > 0) {
      const cardRooms = parseInt(card.getAttribute('data-bedrooms') || '0', 10);
      if (cardRooms !== currentRooms) match = false;
    }

    // Price
    if (match && currentMaxPrice > 0) {
      const cardRent = parseInt(card.getAttribute('data-rent') || '0', 10);
      if (cardRent > currentMaxPrice) match = false;
    }

    // Features
    if (match && activeLegendFeatures.size > 0) {
      for (const f of activeLegendFeatures) {
        if (card.getAttribute('data-has-' + f) !== '1') {
          match = false;
          break;
        }
      }
    }

    card.style.display = match ? '' : 'none';
    if (match) vis++;
  });

  const cEl = document.getElementById('rentalVisibleCount');
  if (cEl) cEl.innerText = vis;

  const clr = document.getElementById('clearFeatureFiltersBtn');
  if (clr) clr.style.display = activeLegendFeatures.size > 0 ? 'inline' : 'none';

  const nr = document.getElementById('rentalNoResults');
  if (nr) nr.style.display = (vis === 0 && cards.length > 0) ? 'block' : 'none';

  const totalActive = activeLegendFeatures.size + (currentIsland !== 'all' ? 1 : 0) + (currentWard ? 1 : 0) + (currentRooms > 0 ? 1 : 0) + (currentMaxPrice > 0 ? 1 : 0);
  const bg = document.getElementById('activeFeatureCountBadge');
  if (bg) {
    bg.style.display = totalActive > 0 ? 'inline-block' : 'none';
    bg.innerText = totalActive + ' active filter' + (totalActive > 1 ? 's' : '');
  }
  const cbg = document.getElementById('collapsedFilterBadge');
  if (cbg) {
    cbg.style.display = totalActive > 0 ? 'inline-block' : 'none';
    cbg.innerText = totalActive + ' active filter' + (totalActive > 1 ? 's' : '');
  }
}

function openAlertModalForCurrentFilter() {
  if (typeof openGlobalAlertsModal === 'function') {
    openGlobalAlertsModal('telegram');
  } else {
    window.location.href = '/alerts';
  }
}
