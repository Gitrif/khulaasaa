/**
 * Khulaasaa Vanilla JS Client Engine
 * 100% Native Browser APIs — Zero external dependencies, zero framework overhead.
 * Manages saved jobs, toast notifications, vacancy alerts, and in-app notification center.
 * Strictly under 500 lines. Zero emojis.
 */

// LocalStorage Saved Jobs Bookmark Manager
function getSavedJobs() {
  try {
    return JSON.parse(localStorage.getItem('khulaasaa_saved_jobs') || '[]');
  } catch (e) {
    return [];
  }
}

function toggleSaveJob(event, btn) {
  if (event) event.stopPropagation();
  const jobId = btn.getAttribute('data-job-id');
  if (!jobId) return;

  let saved = getSavedJobs();
  const idx = saved.indexOf(jobId);
  const svg = btn.querySelector('svg');

  if (idx > -1) {
    saved.splice(idx, 1);
    btn.classList.remove('text-lagoon');
    btn.classList.add('text-slate-400');
    if (svg) svg.setAttribute('fill', 'none');
    btn.title = 'Save this job';
  } else {
    saved.push(jobId);
    btn.classList.remove('text-slate-400');
    btn.classList.add('text-lagoon');
    if (svg) svg.setAttribute('fill', 'currentColor');
    btn.title = 'Job saved';
  }

  localStorage.setItem('khulaasaa_saved_jobs', JSON.stringify(saved));
}

function refreshSavedJobButtons() {
  const saved = getSavedJobs();
  document.querySelectorAll('.save-job-btn').forEach(btn => {
    const jobId = btn.getAttribute('data-job-id');
    const svg = btn.querySelector('svg');
    if (saved.includes(jobId)) {
      btn.classList.remove('text-slate-400');
      btn.classList.add('text-lagoon');
      if (svg) svg.setAttribute('fill', 'currentColor');
      btn.title = 'Job saved';
    }
  });
}

document.addEventListener('DOMContentLoaded', refreshSavedJobButtons);

// Lightweight Toast Notification
function showToast(msg) {
  let toast = document.getElementById('khulaasaa-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'khulaasaa-toast';
    toast.className = 'fixed bottom-20 left-1/2 -translate-x-1/2 bg-ink text-white text-xs font-semibold px-4 py-2.5 rounded-md shadow-lg z-50 transition-opacity duration-200 opacity-0 pointer-events-none flex items-center gap-2';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.remove('opacity-0');
  toast.classList.add('opacity-100');
  setTimeout(() => {
    toast.classList.remove('opacity-100');
    toast.classList.add('opacity-0');
  }, 2400);
}

// Native Share API or Clipboard Copy
function shareJob(event, designation, employer, url) {
  if (event) event.stopPropagation();
  const shareTitle = `${designation} — ${employer}`;
  const shareUrl = url || window.location.href;

  if (navigator.share) {
    navigator.share({
      title: shareTitle,
      text: `Job Opening: ${shareTitle}`,
      url: shareUrl
    }).catch(() => {});
  } else if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(shareUrl).then(() => {
      showToast('Link copied to clipboard!');
    }).catch(() => {
      prompt('Copy link:', shareUrl);
    });
  } else {
    prompt('Copy link:', shareUrl);
  }
}

function handleJobAlertClick(event, discipline, employer) {
  if (event) event.stopPropagation();
  if (typeof isUserAuthenticated === 'function' && !isUserAuthenticated()) {
    if (typeof openGlobalAlertsModal === 'function') {
      openGlobalAlertsModal('auth');
    }
    return;
  }
  openJobAlertModal(event, discipline, employer);
}

// Open Vacancy Alert Modal (Discipline & Employer Alerts)
function openJobAlertModal(event, discipline, employer) {
  if (event) event.stopPropagation();
  const modal = document.getElementById('jobSpecificAlertModal');
  if (!modal) return;

  const discText = document.getElementById('alertModalDisciplineName');
  const empText = document.getElementById('alertModalEmployerName');
  const discCheck = document.getElementById('alertCheckDiscipline');
  const empCheck = document.getElementById('alertCheckEmployer');

  if (discText) discText.textContent = discipline || 'This Discipline';
  if (empText) empText.textContent = employer || 'This Employer';
  if (discCheck) {
    discCheck.value = discipline;
    discCheck.checked = true;
  }
  if (empCheck) {
    empCheck.value = employer;
    empCheck.checked = true;
  }

  modal.classList.remove('hidden');
}

function closeJobAlertModal() {
  const modal = document.getElementById('jobSpecificAlertModal');
  if (modal) modal.classList.add('hidden');
}

async function saveJobAlertPreferences(event) {
  if (event) event.preventDefault();
  const discCheck = document.getElementById('alertCheckDiscipline');
  const empCheck = document.getElementById('alertCheckEmployer');
  const channelEl = document.querySelector('input[name="alertChannel"]:checked');

  const alerts = [];
  if (discCheck && discCheck.checked && discCheck.value) alerts.push({ type: 'discipline', value: discCheck.value });
  if (empCheck && empCheck.checked && empCheck.value) alerts.push({ type: 'employer', value: empCheck.value });
  const channel = channelEl ? channelEl.value : 'telegram';

  try {
    let existing = JSON.parse(localStorage.getItem('khulaasaa_job_alerts') || '[]');
    alerts.forEach(a => {
      if (!existing.some(e => e.type === a.type && e.value === a.value)) {
        existing.push(a);
      }
    });
    localStorage.setItem('khulaasaa_job_alerts', JSON.stringify(existing));
  } catch (e) {}

  try {
    const discValues = alerts.filter(a => a.type === 'discipline').map(a => a.value);
    await fetch('/api/user/job-alerts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ disciplines: discValues })
    });
  } catch (e) {}

  closeJobAlertModal();
  showToast(`Alert set for ${alerts.map(a => a.value).join(' & ')} via ${channel.toUpperCase()}!`);
}

// In-App Notification Center
function closeNotificationsMenu() {
  const menu = document.getElementById('userNotifDropdown');
  if (menu && !menu.classList.contains('hidden')) {
    menu.classList.add('hidden');
  }
}

async function refreshNotificationBadge() {
  try {
    const res = await fetch('/api/account/notifications?limit=5');
    if (!res.ok) return;
    const data = await res.json();
    if (data && data.status === 'ok') {
      const badge = document.getElementById('headerNotifBadge');
      const unread = data.unread_count || 0;
      if (badge) {
        if (unread > 0) {
          badge.textContent = unread > 99 ? '99+' : unread;
          badge.classList.remove('hidden');
        } else {
          badge.classList.add('hidden');
        }
      }
    }
  } catch (err) {}
}

async function toggleNotificationsMenu(e) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }
  if (typeof closeUserAvatarMenu === 'function') closeUserAvatarMenu();
  const menu = document.getElementById('userNotifDropdown');
  if (!menu) return;
  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');
    await loadNotificationsList();
  } else {
    menu.classList.add('hidden');
  }
}

async function loadNotificationsList() {
  const listEl = document.getElementById('userNotifList');
  if (!listEl) return;
  listEl.textContent = '';
  const loadingEl = document.createElement('div');
  loadingEl.className = 'py-6 text-center text-xs text-slate';
  loadingEl.textContent = 'Loading notifications...';
  listEl.appendChild(loadingEl);

  try {
    const res = await fetch('/api/account/notifications?limit=15');
    const data = await res.json();
    listEl.textContent = '';
    if (!res.ok || data.status !== 'ok') {
      const errEl = document.createElement('div');
      errEl.className = 'py-6 text-center text-xs text-red-600';
      errEl.textContent = 'Failed to load notifications.';
      listEl.appendChild(errEl);
      return;
    }
    const notifs = data.notifications || [];
    if (notifs.length === 0) {
      const emptyEl = document.createElement('div');
      emptyEl.className = 'py-8 text-center text-xs text-slate';
      emptyEl.textContent = 'No notifications yet.';
      listEl.appendChild(emptyEl);
      return;
    }

    notifs.forEach(n => {
      const notifId = parseInt(n.id, 10);
      if (isNaN(notifId) || notifId <= 0) return;

      let safeUrl = null;
      if (typeof n.url === 'string' && n.url.startsWith('/') && !n.url.startsWith('//') && !n.url.includes('\\')) {
        safeUrl = n.url;
      }

      const itemEl = document.createElement('div');
      itemEl.className = 'p-3 hover:bg-paper cursor-pointer transition flex items-start gap-2.5 ' + (n.is_read ? 'bg-white' : 'bg-paper-soft');

      if (!n.is_read) {
        const dot = document.createElement('span');
        dot.className = 'w-2 h-2 rounded-full bg-lagoon shrink-0 mt-1';
        itemEl.appendChild(dot);
      }

      const contentCol = document.createElement('div');
      contentCol.className = 'min-w-0 flex-1';

      const titleEl = document.createElement('div');
      titleEl.className = 'text-xs font-semibold text-ink line-clamp-2 leading-tight';
      titleEl.textContent = n.title || 'Alert Notification';
      contentCol.appendChild(titleEl);

      if (n.summary) {
        const sumEl = document.createElement('div');
        sumEl.className = 'text-[11px] text-slate line-clamp-2 mt-0.5';
        sumEl.textContent = n.summary;
        contentCol.appendChild(sumEl);
      }

      const metaEl = document.createElement('div');
      metaEl.className = 'text-[10px] text-slate/70 mt-1 flex items-center gap-2';

      const typeSpan = document.createElement('span');
      typeSpan.className = 'uppercase tracking-wider font-semibold';
      typeSpan.textContent = n.content_type || 'alert';
      metaEl.appendChild(typeSpan);

      if (n.created_at) {
        const timeSpan = document.createElement('span');
        timeSpan.textContent = '• ' + n.created_at.slice(0, 16).replace('T', ' ');
        metaEl.appendChild(timeSpan);
      }

      contentCol.appendChild(metaEl);
      itemEl.appendChild(contentCol);

      itemEl.addEventListener('click', (e) => handleNotificationClick(e, notifId, safeUrl));
      listEl.appendChild(itemEl);
    });
  } catch (err) {
    listEl.textContent = '';
    const netErrEl = document.createElement('div');
    netErrEl.className = 'py-6 text-center text-xs text-red-600';
    netErrEl.textContent = 'Network error.';
    listEl.appendChild(netErrEl);
  }
}

async function handleNotificationClick(e, notifId, url) {
  if (e) e.stopPropagation();
  try {
    await fetch(`/api/account/notifications/${notifId}/read`, { method: 'POST' });
    refreshNotificationBadge();
  } catch (err) {}
  if (url && typeof url === 'string' && url.startsWith('/') && !url.startsWith('//')) {
    window.location.href = url;
  } else {
    await loadNotificationsList();
  }
}

async function markAllNotificationsAsRead() {
  try {
    await fetch('/api/account/notifications/read-all', { method: 'POST' });
    refreshNotificationBadge();
    await loadNotificationsList();
  } catch (err) {}
}
