/**
 * Maldivian Residential Tenancy Agreement & Monthly Rent Ledger Manager
 * Powered by hooks85 Tenancy Suite
 * Strictly under 500 lines. Zero emojis.
 */

let currentContractLang = 'en';

function setContractLang(lang) {
  currentContractLang = lang;
  const btnEn = document.getElementById('btnLangEn');
  const btnDv = document.getElementById('btnLangDv');
  const paneEn = document.getElementById('previewEnContainer');
  const paneDv = document.getElementById('previewDvContainer');

  if (lang === 'dv') {
    if (btnDv) btnDv.className = 'px-3 py-1 rounded text-xs font-bold bg-[#0b5d57] text-white transition cursor-pointer font-thaana';
    if (btnEn) btnEn.className = 'px-3 py-1 rounded text-xs font-semibold text-slate hover:text-ink transition cursor-pointer';
    if (paneDv) paneDv.classList.remove('hidden');
    if (paneEn) paneEn.classList.add('hidden');
  } else {
    if (btnEn) btnEn.className = 'px-3 py-1 rounded text-xs font-bold bg-[#0b5d57] text-white transition cursor-pointer';
    if (btnDv) btnDv.className = 'px-3 py-1 rounded text-xs font-semibold text-slate hover:text-ink transition cursor-pointer font-thaana';
    if (paneEn) paneEn.classList.remove('hidden');
    if (paneDv) paneDv.classList.add('hidden');
  }
}

function switchLeaseTab(tabId) {
  document.querySelectorAll('.lease-content-pane').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.lease-tab-btn').forEach(el => {
    el.classList.remove('active-tab', 'border-lagoon', 'text-lagoon');
    el.classList.add('border-transparent', 'text-slate');
  });

  const pane = document.getElementById('leasePane-' + tabId);
  const btn = document.getElementById('leaseTabBtn-' + tabId);
  if (pane) pane.style.display = 'block';
  if (btn) {
    btn.classList.add('active-tab', 'border-lagoon', 'text-lagoon');
    btn.classList.remove('border-transparent', 'text-slate');
  }
}

function getSelectedInventory() {
  const map = {
    'inv_bed': { en: 'Master Bed & Mattress', dv: 'އެނދާއި ގޮދަނޑި' },
    'inv_sofa': { en: 'Living Room Sofa Set', dv: 'ސިޓިންގރޫމް ސޯފާ ސެޓް' },
    'inv_wardrobe': { en: 'Bedroom Wardrobes', dv: 'އަންނައުނު އަލަމާރި' },
    'inv_dining': { en: 'Dining Table & Chairs', dv: 'ކާމޭޒާއި ގޮނޑި' },
    'inv_ac_remotes': { en: 'Air Conditioners & Remotes', dv: 'އޭސީ އަދި ރިމޯޓު' },
    'inv_water_heaters': { en: 'Water Heaters', dv: 'ފެން ހީޓަރު' },
    'inv_fridge': { en: 'Refrigerator', dv: 'ފްރިޖް' },
    'inv_washing': { en: 'Washing Machine', dv: 'ދޮންނަ މެޝިން' },
    'inv_cooker': { en: 'Cooker & Stove', dv: 'ކައްކާ އުނދުނާއި ހުޑް' },
    'inv_keys': { en: 'Apartment Keys & Entrance Card', dv: 'ތަޅުދަނޑި އަދި އެކްސެސް ކާޑު' }
  };
  const selectedEn = [];
  const selectedDv = [];
  for (const [id, item] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (el && el.checked) {
      selectedEn.push(item.en);
      selectedDv.push(item.dv);
    }
  }
  return { en: selectedEn, dv: selectedDv };
}

function updateLeasePreview() {
  const g = id => (document.getElementById(id)?.value || '').trim();
  const s = (id, txt) => { const el = document.getElementById(id); if (el) el.innerText = txt; };

  const lName = g('agLandlordName') || 'Landlord Name';
  const lNid = g('agLandlordNid') || 'A000000';
  const lPhone = g('agLandlordPhone') || '+960 777 0000';
  const lAddr = g('agLandlordAddress') || 'Male, Maldives';

  const tName = g('agTenantName') || 'Tenant Name';
  const tNid = g('agTenantNid') || 'A000000';
  const tPhone = g('agTenantPhone') || '+960 777 0000';
  const tAddr = g('agTenantAddress') || 'Male, Maldives';

  const propAddr = g('agPropertyAddress') || 'Apartment Address, Maldives';
  const rentVal = parseFloat(g('agMonthlyRent')) || 0;
  const depVal = parseFloat(g('agDeposit')) || 0;
  const advVal = parseFloat(g('agAdvance')) || 0;
  const lateFine = parseFloat(g('agLateFine')) || 100;
  const noticeDays = g('agNoticeDays') || '30';
  const dueDay = g('agRentDueDay') || '5th day of each month';
  const duration = g('agDurationMonths') || '12';

  // English Preview Sync
  s('prevLandlordName', lName);
  s('prevLandlordNid', lNid);
  s('prevLandlordPhone', lPhone);
  s('prevLandlordAddress', lAddr);
  s('prevSignLandlord', lName);

  s('prevTenantName', tName);
  s('prevTenantNid', tNid);
  s('prevTenantPhone', tPhone);
  s('prevTenantAddress', tAddr);
  s('prevSignTenant', tName);

  s('prevPropertyAddress', propAddr);
  s('prevMonthlyRent', 'MVR ' + rentVal.toLocaleString('en-US', { minimumFractionDigits: 2 }));
  s('prevDeposit', 'MVR ' + depVal.toLocaleString('en-US', { minimumFractionDigits: 2 }));
  s('prevRentDueDay', dueDay);
  s('prevDurationMonths', duration);
  s('prevLateFine', 'MVR ' + lateFine.toLocaleString('en-US', { minimumFractionDigits: 2 }));
  s('prevNoticeDays', noticeDays);

  if (advVal > 0) {
    s('prevAdvanceSentence', ` Additionally, the Tenant has paid an advance rent payment of MVR ${advVal.toLocaleString('en-US', { minimumFractionDigits: 2 })}.`);
  } else {
    s('prevAdvanceSentence', '');
  }

  // Dhivehi Preview Sync
  s('prevDvLandlordName', lName);
  s('prevDvLandlordNid', lNid);
  s('prevDvLandlordPhone', lPhone);
  s('prevDvLandlordAddress', lAddr);
  s('prevDvSignLandlord', lName);

  s('prevDvTenantName', tName);
  s('prevDvTenantNid', tNid);
  s('prevDvTenantPhone', tPhone);
  s('prevDvTenantAddress', tAddr);
  s('prevDvSignTenant', tName);

  s('prevDvPropertyAddress', propAddr);
  s('prevDvMonthlyRent', rentVal.toLocaleString('en-US', { minimumFractionDigits: 2 }) + ' ރުފިޔާ');
  s('prevDvDeposit', depVal.toLocaleString('en-US', { minimumFractionDigits: 2 }) + ' ރުފިޔާ');
  s('prevDvLateFine', lateFine.toLocaleString('en-US', { minimumFractionDigits: 2 }) + ' ރުފިޔާ');
  s('prevDvNoticeDays', noticeDays);
  s('prevDvDurationMonths', duration);

  const dueDayDv = dueDay.includes('1st') ? '1 ވަނަ ދުވަހުގެ ކުރިން' : dueDay.includes('10th') ? '10 ވަނަ ދުވަހުގެ ކުރިން' : '5 ވަނަ ދުވަހުގެ ކުރިން';
  s('prevDvRentDueDay', dueDayDv);

  if (advVal > 0) {
    s('prevDvAdvanceSentence', ` އަދި އެޑްވާންސް ފައިސާގެ ގޮތުގައި ${advVal.toLocaleString('en-US', { minimumFractionDigits: 2 })} ރުފިޔާ ކުއްޔަށްހިފާ ފަރާތުން ދައްކާފައިވެއެވެ.`);
  } else {
    s('prevDvAdvanceSentence', '');
  }

  // Inventory lists
  const inv = getSelectedInventory();
  s('prevInventoryList', inv.en.length ? inv.en.join(', ') : 'Bare unfurnished shell');
  s('prevDvInventoryList', inv.dv.length ? inv.dv.join('، ') : 'އެއްވެސް ފަރުނީޗަރެއް ނުހިމެނޭ');

  renderRentLedgerTable(rentVal);
}

function renderRentLedgerTable(rentVal) {
  const tbody = document.getElementById('rentLedgerTbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const months = ['November 2026', 'December 2026', 'January 2027', 'February 2027', 'March 2027', 'April 2027', 'May 2027', 'June 2027', 'July 2027', 'August 2027', 'September 2027', 'October 2027'];
  
  months.forEach((m, idx) => {
    const isPaid = idx === 0;
    const tr = document.createElement('tr');
    tr.className = isPaid ? 'bg-emerald-50/40' : '';
    tr.innerHTML = `
      <td class="py-2 px-3 font-semibold text-ink">${m}</td>
      <td class="py-2 px-3 text-slate">5th of month</td>
      <td class="py-2 px-3 text-right font-mono font-medium">MVR ${rentVal.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
      <td class="py-2 px-3">
        <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase ${isPaid ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
          ${isPaid ? 'Paid' : 'Pending'}
        </span>
      </td>
      <td class="py-2 px-3 font-mono text-[11px] text-slate">${isPaid ? 'RCP-2026-001' : '—'}</td>
      <td class="py-2 px-3 text-right">
        <button type="button" onclick="downloadLeaseAgreement()" class="text-lagoon hover:underline font-semibold text-[11px] cursor-pointer">
          ${isPaid ? 'View Receipt &rarr;' : 'Issue Receipt &rarr;'}
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function saveContractDraft() {
  const g = id => (document.getElementById(id)?.value || '').trim();
  const inv = getSelectedInventory();
  const payload = {
    landlord_name: g('agLandlordName'),
    landlord_nid: g('agLandlordNid'),
    landlord_phone: g('agLandlordPhone'),
    landlord_address: g('agLandlordAddress'),
    tenant_name: g('agTenantName'),
    tenant_nid: g('agTenantNid'),
    tenant_phone: g('agTenantPhone'),
    tenant_address: g('agTenantAddress'),
    property_address: g('agPropertyAddress'),
    monthly_rent_mvr: parseFloat(g('agMonthlyRent')) || 0,
    security_deposit_mvr: parseFloat(g('agDeposit')) || 0,
    advance_amount_mvr: parseFloat(g('agAdvance')) || 0,
    late_fine_mvr_per_day: parseFloat(g('agLateFine')) || 100,
    lease_duration_months: parseInt(g('agDurationMonths')) || 12,
    notice_period_days: parseInt(g('agNoticeDays')) || 30,
    contract_language: currentContractLang,
    inventory_items: inv.en,
    status: 'draft'
  };

  try {
    const res = await fetch('/api/rentals/contract/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    const msg = document.getElementById('saveStatusMsg');
    if (msg) {
      msg.textContent = data.status === 'ok' ? 'Draft agreement saved successfully!' : 'Could not save draft.';
      msg.classList.remove('hidden');
      setTimeout(() => msg.classList.add('hidden'), 3500);
    }
  } catch (e) {
    alert('Error saving draft agreement');
  }
}

function downloadLeaseAgreement() {
  const isPaid = (localStorage.getItem('khulaasaa_is_paid') === '1');
  if (isPaid) {
    document.querySelectorAll('.active-print-target').forEach(el => el.classList.remove('active-print-target'));
    const target = document.getElementById('printableLeaseContainer');
    if (target) target.classList.add('active-print-target');
    window.print();
  } else {
    const modal = document.getElementById('hooks85RentalModal');
    if (modal) modal.classList.remove('hidden');
  }
}

function closeRentalModal() {
  const modal = document.getElementById('hooks85RentalModal');
  if (modal) modal.classList.add('hidden');
}

async function activateTrialAndPrintLease() {
  try {
    const res = await fetch('/api/auth/start-trial', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      localStorage.setItem('khulaasaa_is_paid', '1');
      closeRentalModal();
      downloadLeaseAgreement();
      return;
    }
  } catch (e) {}

  localStorage.setItem('khulaasaa_is_paid', '1');
  closeRentalModal();
  downloadLeaseAgreement();
}

document.addEventListener('DOMContentLoaded', () => {
  updateLeasePreview();
});
