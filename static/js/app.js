/**
 * Khulaasaa Vanilla JS Client Engine
 * 100% Native Browser APIs — Zero external dependencies, zero framework overhead.
 */

// Native Partial Loader (fetches Jinja2 HTML component snippet and swaps DOM target)
async function loadPartial(url, targetSelector, pushState = true) {
  const target = document.querySelector(targetSelector);
  if (!target) {
    window.location.href = url;
    return;
  }

  target.style.opacity = '0.5';
  target.style.transition = 'opacity 0.15s ease';

  try {
    const res = await fetch(url, {
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'text/html'
      }
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const html = await res.text();
    target.innerHTML = html;

    if (pushState && window.history && window.history.pushState) {
      window.history.pushState({ partialUrl: url, target: targetSelector }, '', url);
    }
  } catch (err) {
    console.error('Failed to load partial content:', err);
    // Graceful fallback: navigate full page
    window.location.href = url;
  } finally {
    target.style.opacity = '1';
  }
}

// Global click delegation for partial-enabled links
document.addEventListener('click', function (e) {
  const trigger = e.target.closest('[data-partial-target]');
  if (!trigger) return;

  const targetSelector = trigger.getAttribute('data-partial-target');
  const url = trigger.getAttribute('href') || trigger.getAttribute('data-url');
  if (!url || !targetSelector) return;

  e.preventDefault();

  // Update active pill UI if in a filter bar
  const pillBar = trigger.closest('.filter-pills, .tagnav');
  if (pillBar) {
    pillBar.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
    trigger.classList.add('active');
  }

  loadPartial(url, targetSelector, true);
});

// Handle browser Back / Forward buttons with partial state
window.addEventListener('popstate', function (e) {
  if (e.state && e.state.partialUrl) {
    const target = e.state.target ? document.querySelector(e.state.target) : null;
    if (target) {
      loadPartial(e.state.partialUrl, e.state.target, false);
    } else {
      window.location.href = e.state.partialUrl || '/';
    }
  }
});

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

  // Save to localStorage
  try {
    let existing = JSON.parse(localStorage.getItem('khulaasaa_job_alerts') || '[]');
    alerts.forEach(a => {
      if (!existing.some(e => e.type === a.type && e.value === a.value)) {
        existing.push(a);
      }
    });
    localStorage.setItem('khulaasaa_job_alerts', JSON.stringify(existing));
  } catch (e) {}

  // If user is authenticated, post to backend API
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
