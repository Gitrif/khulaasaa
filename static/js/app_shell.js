/**
 * Global App Shell and User Interface Controller for Khulaasaa.
 * Manages Telegram WebApp integration, user authentication state,
 * avatar menu, story sharing, following, and filter drawer state.
 * Strictly under 500 lines. Zero emojis.
 */

function isLikelyTelegramWebView() {
  if (window.TelegramWebviewProxy || window.TelegramWebviewProxyProto || window.TelegramWebview) {
    return true;
  }
  const search = window.location.search || '';
  const hash = window.location.hash || '';
  return search.includes('tgWebAppData=') || hash.includes('tgWebAppData=') || /Telegram/i.test(navigator.userAgent || '');
}

function initTelegramMiniApp(tg) {
  if (!tg || typeof tg.initData !== 'string' || !tg.initData.trim()) {
    return;
  }
  try {
    tg.ready();
    tg.expand();
    if (tg.isVersionAtLeast && tg.isVersionAtLeast('6.1') && tg.setHeaderColor) {
      tg.setHeaderColor('#10222E');
    }
    document.documentElement.classList.add('telegram-webapp');

    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
      handleTelegramMiniAppUser(tg.initDataUnsafe.user);
    }

    document.addEventListener('click', function(e) {
      const a = e.target.closest('a');
      if (a && a.href) {
        const url = new URL(a.href, window.location.href);
        if (url.origin !== window.location.origin || a.target === '_blank') {
          if (url.protocol.startsWith('http')) {
            e.preventDefault();
            tg.openLink(a.href);
          }
        }
      }
    });
  } catch (err) {
    console.warn('Telegram Mini App initialization error:', err);
  }
}

document.addEventListener('DOMContentLoaded', function() {
  const existingTg = window.Telegram && window.Telegram.WebApp;
  if (existingTg && typeof existingTg.initData === 'string' && existingTg.initData.trim()) {
    initTelegramMiniApp(existingTg);
  } else if (isLikelyTelegramWebView()) {
    const sdkScript = document.createElement('script');
    sdkScript.src = 'https://telegram.org/js/telegram-web-app.js';
    sdkScript.defer = true;
    sdkScript.onload = function() {
      const loadedTg = window.Telegram && window.Telegram.WebApp;
      if (loadedTg && typeof loadedTg.initData === 'string' && loadedTg.initData.trim()) {
        initTelegramMiniApp(loadedTg);
      }
    };
    sdkScript.onerror = function(err) {
      console.warn('Failed to load Telegram WebApp SDK:', err);
    };
    document.head.appendChild(sdkScript);
  }

  refreshGlobalAuthPill();
});

function getUserInitials(name, email) {
  const src = (name || email || 'U').trim();
  const parts = src.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return src.substring(0, 2).toUpperCase();
}

function toggleUserAvatarMenu(e) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }
  const menu = document.getElementById('userAvatarDropdown');
  if (menu) {
    menu.classList.toggle('hidden');
  }
}

function closeUserAvatarMenu() {
  const menu = document.getElementById('userAvatarDropdown');
  if (menu && !menu.classList.contains('hidden')) {
    menu.classList.add('hidden');
  }
}

document.addEventListener('click', function(e) {
  const avatarContainer = document.getElementById('userAvatarMenuContainer');
  if (avatarContainer && !avatarContainer.contains(e.target)) {
    closeUserAvatarMenu();
  }
  const notifContainer = document.getElementById('userNotificationsContainer');
  if (notifContainer && !notifContainer.contains(e.target)) {
    if (typeof closeNotificationsMenu === 'function') closeNotificationsMenu();
  }
});

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeUserAvatarMenu();
    if (typeof closeNotificationsMenu === 'function') closeNotificationsMenu();
    if (typeof closeGlobalAlertsModal === 'function') closeGlobalAlertsModal();
    if (typeof closeSourcesModal === 'function') closeSourcesModal();
    if (typeof closeJobAlertModal === 'function') closeJobAlertModal();
    if (typeof closeFeedbackModal === 'function') closeFeedbackModal();
    const advM = document.getElementById('advancedFilterModal');
    if (advM && !advM.classList.contains('hidden')) {
      if (typeof closeAdvancedFilterModal === 'function') closeAdvancedFilterModal();
      else advM.classList.add('hidden');
    }
  }
});

function handleHeaderChannelClick(channel) {
  const avatarContainer = document.getElementById('userAvatarMenuContainer');
  if (avatarContainer) {
    window.location.href = '/account/channels';
  } else if (typeof openGlobalAlertsModal === 'function') {
    openGlobalAlertsModal(channel);
  }
}

async function refreshGlobalAuthPill() {
  const container = document.getElementById('globalUserPillContainer');
  const viberBtn = document.getElementById('headerViberBtn');
  const tgBtn = document.getElementById('headerTelegramBtn');
  const notifContainer = document.getElementById('userNotificationsContainer');

  let user = null;
  try {
    const res = await fetch('/api/auth/me');
    const data = await res.json();
    if (data && data.user) {
      user = data.user;
    }
  } catch (err) {
    console.warn('Auth status check failed:', err);
  }

  const isTgConnected = Boolean(user && user.telegram_verified && user.telegram_chat_id);
  const isViberConnected = Boolean(user && user.viber_verified && user.viber_user_id);

  if (viberBtn) {
    if (isViberConnected) {
      viberBtn.classList.add('active-viber');
      viberBtn.title = 'Viber Verified (' + user.viber_user_id + ') — Click to Manage';
    } else {
      viberBtn.classList.remove('active-viber');
      viberBtn.title = user ? 'Connect & Verify Viber Alerts' : 'Connect Viber Alerts';
    }
  }

  if (tgBtn) {
    if (isTgConnected) {
      tgBtn.classList.add('active-telegram');
      tgBtn.title = 'Telegram Verified (' + user.telegram_chat_id + ') — Click to Manage';
    } else {
      tgBtn.classList.remove('active-telegram');
      tgBtn.title = user ? 'Connect & Verify Telegram Alerts' : 'Connect Telegram Alerts';
    }
  }

  if (notifContainer) {
    if (user) {
      notifContainer.classList.remove('hidden');
      if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
    } else {
      notifContainer.classList.add('hidden');
    }
  }
  if (!container) return;

  if (user) {
    renderUserAvatarMenu(container, user);
  } else {
    renderGuestAvatarButton(container);
  }
}

function renderUserAvatarMenu(container, u) {
  container.textContent = '';
  window.SERVER_IS_PAID = Boolean(u.is_paid);

  const tpl = document.getElementById('userAvatarMenuTemplate');
  if (!tpl) return;
  const clone = tpl.content.cloneNode(true);

  const initials = getUserInitials(u.full_name, u.email);
  const displayName = (u.full_name || (u.email ? u.email.split('@')[0] : 'Member')).trim();

  const triggerBtn = clone.querySelector('#userAvatarTrigger');
  if (triggerBtn) {
    triggerBtn.title = 'Account Menu for ' + displayName;
    triggerBtn.addEventListener('click', toggleUserAvatarMenu);
  }

  const initEl = clone.querySelector('#userAvatarInitials');
  if (initEl) initEl.textContent = initials;

  const nameEl = clone.querySelector('#userAvatarDisplayName');
  if (nameEl) nameEl.textContent = displayName;

  const dropInitEl = clone.querySelector('#userDropdownInitials');
  if (dropInitEl) dropInitEl.textContent = initials;

  const dropFullEl = clone.querySelector('#userDropdownFullName');
  if (dropFullEl) dropFullEl.textContent = (u.full_name || displayName).trim();

  const dropEmailEl = clone.querySelector('#userDropdownEmail');
  if (dropEmailEl) dropEmailEl.textContent = (u.email || '').trim();

  const tierBadge = clone.querySelector('#userDropdownTierBadge');
  if (tierBadge) {
    tierBadge.textContent = u.is_paid ? 'PRO' : 'Free';
    tierBadge.className = u.is_paid
      ? 'px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300'
      : 'px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200';
  }

  container.appendChild(clone);
}

function renderGuestAvatarButton(container) {
  container.textContent = '';
  const guestBtn = document.createElement('button');
  guestBtn.className = 'app-icon-btn app-icon-btn-round';
  guestBtn.title = 'Sign In / Register';
  guestBtn.setAttribute('aria-label', 'Sign In');
  guestBtn.addEventListener('click', () => openGlobalAlertsModal('auth'));

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'w-4 h-4 text-slate fill-current');
  svg.setAttribute('viewBox', '0 0 24 24');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z');
  svg.appendChild(path);
  guestBtn.appendChild(svg);
  container.appendChild(guestBtn);
}

async function handleGlobalLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (e) {}
  localStorage.removeItem('khulaasaa_tg_connected');
  localStorage.removeItem('khulaasaa_viber_connected');
  localStorage.removeItem('khulaasaa_tg_name');
  localStorage.removeItem('khulaasaa_is_paid');
  localStorage.removeItem('khulaasaa_user_id');
  localStorage.removeItem('khulaasaa_user_email');
  sessionStorage.removeItem('khulaasaa_auth_next');
  sessionStorage.removeItem('khulaasaa_pending_follow');
  refreshGlobalAuthPill();
  window.location.href = '/';
}

async function toggleFollow(targetType, targetId, targetTitle, btnElement) {
  if (!targetType || !targetId) return;
  try {
    const meRes = await fetch('/api/auth/me');
    const meData = await meRes.json();
    if (!meData || !meData.user) {
      sessionStorage.setItem('khulaasaa_pending_follow', JSON.stringify({
        target_type: targetType,
        target_id: targetId,
        target_title: targetTitle || targetId
      }));
      if (typeof openGlobalAlertsModal === 'function') {
        openGlobalAlertsModal('auth');
      }
      return;
    }

    const isFollowing = btnElement && (btnElement.getAttribute('data-following') === 'true' || btnElement.classList.contains('active-following'));
    if (isFollowing) {
      const res = await fetch(`/api/follows?target_type=${encodeURIComponent(targetType)}&target_id=${encodeURIComponent(targetId)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        if (btnElement) {
          btnElement.setAttribute('data-following', 'false');
          btnElement.classList.remove('active-following');
          const label = btnElement.querySelector('.follow-label') || btnElement;
          if (label) label.textContent = 'Follow';
        }
      }
    } else {
      const res = await fetch('/api/follows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_type: targetType,
          target_id: targetId,
          target_title: targetTitle || targetId
        })
      });
      if (res.ok) {
        if (btnElement) {
          btnElement.setAttribute('data-following', 'true');
          btnElement.classList.add('active-following');
          const label = btnElement.querySelector('.follow-label') || btnElement;
          if (label) label.textContent = 'Following';
        }
      }
    }
  } catch (err) {
    console.error('Follow toggle error:', err);
  }
}
window.toggleFollow = toggleFollow;

async function handleTelegramMiniAppUser(user) {
  if (!user) return;
  try {
    const res = await fetch('/api/auth/telegram-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        init_data: (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) || '',
      })
    });
    const d = await res.json();
    if (d.status === 'ok') {
      refreshGlobalAuthPill();
    }
  } catch (err) {
    console.warn('Telegram Mini App login failed:', err);
  }
}

function handleGlobalSearch(query) {
  if (typeof filterCards === 'function') {
    filterCards(query);
    return;
  }
  const obitSearch = document.getElementById('obituarySearch') || document.getElementById('searchInput');
  if (obitSearch && typeof applyFilters === 'function') {
    obitSearch.value = query || '';
    applyFilters();
    return;
  }
  const rentalSearch = document.getElementById('rentalSearchInput');
  if (rentalSearch && typeof applyAllCardFilters === 'function') {
    rentalSearch.value = query || '';
    applyAllCardFilters();
  }
}
window.handleGlobalSearch = handleGlobalSearch;

function isMobileDevice() {
  return /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent || '');
}

function shareStory(evt, headline, url) {
  if (evt) evt.stopPropagation();
  const fullUrl = url && url.startsWith('http') ? url : window.location.origin + (url || '');
  const shareText = (headline || 'Khulaasaa') + ' — Khulaasaa Dispatch';
  const tgShareUrl = 'https://t.me/share/url?url=' + encodeURIComponent(fullUrl) + '&text=' + encodeURIComponent(shareText);

  if (navigator.share) {
    navigator.share({
      title: headline,
      text: shareText,
      url: fullUrl
    }).catch(() => {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(fullUrl).then(() => {
      alert('Link copied to clipboard: ' + fullUrl);
    }).catch(() => {
      window.open(tgShareUrl, '_blank');
    });
  } else {
    window.open(tgShareUrl, '_blank');
  }
}

/* Shared accessible filter drawer controller used by page filter toolbars. */
function toggleFilterDrawer() {
  const drawer = document.getElementById('filterDrawer');
  const trigger = document.getElementById('toggleFilterBtn');
  if (!drawer || !trigger) return;
  const willOpen = drawer.classList.contains('hidden');
  drawer.classList.toggle('hidden', !willOpen);
  trigger.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
  trigger.setAttribute('aria-controls', 'filterDrawer');
}
window.toggleFilterDrawer = toggleFilterDrawer;
