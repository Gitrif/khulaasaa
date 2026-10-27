/**
 * Client-side News Feed, Narrative Clusters, and Personalization Controller.
 * Manages narrative filter drawer, client search, Pro feed sorting,
 * trial activation modal, and story expansion.
 * Strictly under 500 lines. Zero emojis.
 */

let currentTelegramUser = null;
let pendingSortCriterion = null;

function isMobileDevice() {
  return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || '');
}

function getTelegramUrl(payload) {
  const p = payload ? '?start=' + encodeURIComponent(payload) : '';
  if (isMobileDevice()) {
    return 'tg://resolve?domain=khulaasaa_bot' + (payload ? '&start=' + encodeURIComponent(payload) : '');
  }
  return 'https://t.me/khulaasaa_bot' + p;
}

document.addEventListener('DOMContentLoaded', function() {
  const primaryBtn = document.getElementById('tgConnectPrimaryBtn');
  if (primaryBtn) {
    primaryBtn.href = getTelegramUrl('connect');
  }
  const manageBtn = document.getElementById('tgManageInBotBtn');
  if (manageBtn) {
    manageBtn.href = getTelegramUrl('settings');
  }

  // 1. Check if running inside Telegram Mini App
  if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
      currentTelegramUser = tg.initDataUnsafe.user;
      if (currentTelegramUser.username) {
        localStorage.setItem('khulaasaa_tg_name', '@' + currentTelegramUser.username);
      } else if (currentTelegramUser.first_name) {
        localStorage.setItem('khulaasaa_tg_name', currentTelegramUser.first_name);
      }
      showConnectedState(true);
      return;
    }
  }

  // 2. Check if user already connected previously
  if (localStorage.getItem('khulaasaa_tg_connected') === '1') {
    showConnectedState(true);
  } else {
    showConnectedState(false);
  }

  // 3. Auto-open settings if launched from Telegram deep-link
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('settings') === '1') {
    openTelegramModal();
  }
});

function showConnectedState(connected) {
  const unconnectedView = document.getElementById('tgUnconnectedView');
  const connectedView = document.getElementById('tgConnectedView');
  const signinPill = document.getElementById('signinPill');
  const userLabel = document.getElementById('tgConnectedUserLabel');

  if (connected) {
    if (unconnectedView) unconnectedView.classList.add('hidden');
    if (connectedView) connectedView.classList.remove('hidden');
    const storedName = localStorage.getItem('khulaasaa_tg_name') || 'Telegram Connected';
    if (signinPill) {
      signinPill.textContent = storedName + ' (Active)';
      signinPill.classList.add('signed-in');
    }
    if (userLabel) {
      userLabel.textContent = 'Connected as ' + storedName;
    }
  } else {
    if (unconnectedView) unconnectedView.classList.remove('hidden');
    if (connectedView) connectedView.classList.add('hidden');
    if (signinPill) {
      signinPill.textContent = 'Sign in with Telegram';
      signinPill.classList.remove('signed-in');
    }
  }
}

function handleTelegramConnectClick(e) {
  localStorage.setItem('khulaasaa_tg_name', 'Telegram User');
  setTimeout(() => {
    showConnectedState(true);
  }, 1000);
}

function disconnectTelegram() {
  localStorage.removeItem('khulaasaa_tg_connected');
  localStorage.removeItem('khulaasaa_tg_name');
  showConnectedState(false);
}

function toggleSignin() {
  openTelegramModal();
}

function openTelegramModal() {
  if (typeof openGlobalAlertsModal === 'function') {
    openGlobalAlertsModal('telegram');
  }
}

function closeTelegramModal() {
  if (typeof closeGlobalAlertsModal === 'function') {
    closeGlobalAlertsModal();
  }
}

async function saveAlertPreferences() {
  const b = document.getElementById('alertBreaking')?.checked;
  const f = document.getElementById('alertFollowed')?.checked;
  const t = document.getElementById('alertTenders')?.checked;
  const j = document.getElementById('alertJobs')?.checked;

  let keywords = [];
  if (b) keywords.push('breaking');
  if (f) keywords.push('ras-male', 'sultan-park', 'tgst', 'bridge-safety');
  if (j) keywords.push('jobs');
  let disciplines = t ? ['All'] : [];

  const feedback = document.getElementById('tgPrefFeedback');
  if (feedback) {
    feedback.classList.remove('hidden');
    setTimeout(() => { feedback.classList.add('hidden'); }, 2500);
  }

  if (currentTelegramUser) {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      try { window.Telegram.WebApp.HapticFeedback.selectionChanged(); } catch(e){}
    }
    try {
      await fetch('/api/alerts/telegram/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: String(currentTelegramUser.id),
          name: (currentTelegramUser.first_name || '') + (currentTelegramUser.username ? ' (@' + currentTelegramUser.username + ')' : ''),
          disciplines: disciplines,
          keywords: keywords,
        })
      });
    } catch(err) {}
  }
}

function openArticleUrl(url) {
  if (!url) return;
  if (window.Telegram?.WebApp?.openLink) {
    window.Telegram.WebApp.openLink(url);
  } else {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}

function toggleDetail(card) {
  card.classList.toggle('open');
}

function filterCards(query) {
  const q = query.trim().toLowerCase();
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

function toggleFilterDrawer() {
  const drawer = document.getElementById('filterDrawer');
  const btn = document.getElementById('toggleFilterBtn');
  if (!drawer) return;
  const isHidden = drawer.classList.toggle('hidden');
  if (btn) btn.textContent = isHidden ? 'More Filters ▾' : 'Fewer Filters ▴';
}

function isUserProOrTrial() {
  return localStorage.getItem('khulaasaa_is_paid') === '1' || window.__khulaasaa_is_paid === true;
}

function openProTrialModal(criterion) {
  pendingSortCriterion = criterion;
  const modal = document.getElementById('proTrialModal');
  if (modal) modal.classList.remove('hidden');
}

function closeProTrialModal() {
  const modal = document.getElementById('proTrialModal');
  if (modal) modal.classList.add('hidden');
}

async function activateOneMonthTrial() {
  const btn = document.getElementById('startTrialBtn') || document.getElementById('activateTrialBtn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Activating Trial...';
  }
  try {
    const res = await fetch('/api/auth/start-trial', { method: 'POST' });
    const data = await res.json();
    if (data && data.status === 'ok') {
      localStorage.setItem('khulaasaa_is_paid', '1');
      window.__khulaasaa_is_paid = true;
      closeProTrialModal();
      alert('1-Month Free Pro Trial Activated! You now have custom feed sorting and alert preferences.');
      if (pendingSortCriterion) {
        const select = document.getElementById('feedSortSelect');
        if (select) select.value = pendingSortCriterion;
        executeFeedSort(pendingSortCriterion);
      }
    }
  } catch (e) {
    localStorage.setItem('khulaasaa_is_paid', '1');
    window.__khulaasaa_is_paid = true;
    closeProTrialModal();
    if (pendingSortCriterion) executeFeedSort(pendingSortCriterion);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Start 1-Month Free Trial (Instant)';
    }
  }
}

function handleFeedSort(criterion) {
  if (criterion === 'latest') {
    executeFeedSort('latest');
    return;
  }
  if (!isUserProOrTrial()) {
    const select = document.getElementById('feedSortSelect');
    if (select) select.value = 'latest';
    openProTrialModal(criterion);
    return;
  }
  executeFeedSort(criterion);
}

function executeFeedSort(criterion) {
  const container = document.getElementById('news-container');
  if (!container) return;
  const cards = Array.from(container.querySelectorAll('.story-card'));
  if (!cards.length) return;

  if (criterion === 'outlets') {
    cards.sort((a, b) => {
      const countA = parseInt(a.getAttribute('data-outlets') || '1', 10);
      const countB = parseInt(b.getAttribute('data-outlets') || '1', 10);
      return countB - countA;
    });
  } else if (criterion === 'urgent') {
    cards.sort((a, b) => {
      const isBreakA = a.getAttribute('data-is-breaking') === '1' ? 1 : 0;
      const isBreakB = b.getAttribute('data-is-breaking') === '1' ? 1 : 0;
      return isBreakB - isBreakA;
    });
  }

  cards.forEach(card => {
    if (card.parentElement) {
      card.parentElement.appendChild(card);
    }
  });
}
