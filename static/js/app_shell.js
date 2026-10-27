/**
 * Global App Shell and User Interface Controller for Khulaasaa.
 * Manages Telegram WebApp integration, user authentication state,
 * avatar menu, notifications dropdown, story sharing, and following.
 * Strictly under 500 lines. Zero emojis.
 */

document.addEventListener('DOMContentLoaded', function() {
  if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    try {
      tg.ready();
      tg.expand();
      if (tg.isVersionAtLeast && tg.isVersionAtLeast('6.1') && tg.setHeaderColor) {
        tg.setHeaderColor('#10222E');
      }
      document.documentElement.classList.add('telegram-webapp');

      // Auto-sign in if launched inside Telegram Mini App
      if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        handleTelegramMiniAppUser(tg.initDataUnsafe.user);
      }

      // Intercept external links
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
    } catch(e) {}
  }

  // Check current session on load
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

function closeNotificationsMenu() {
  const menu = document.getElementById('userNotifDropdown');
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
    closeNotificationsMenu();
  }
});

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeUserAvatarMenu();
    closeNotificationsMenu();
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
  } else {
    openGlobalAlertsModal(channel);
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
  closeUserAvatarMenu();
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
  } catch (err) {}

  // Truthful verification status derived strictly from verified backend records
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

  // In-app notifications indicator
  if (notifContainer) {
    if (user) {
      notifContainer.classList.remove('hidden');
      refreshNotificationBadge();
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
  if (u.is_paid) {
    localStorage.setItem('khulaasaa_is_paid', '1');
  }

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
        chat_id: String(user.id),
        username: user.username || '',
        first_name: user.first_name || '',
      })
    });
    const d = await res.json();
    if (d.status === 'ok') {
      localStorage.setItem('khulaasaa_tg_name', user.username ? '@' + user.username : user.first_name);
      refreshGlobalAuthPill();
    }
  } catch (err) {}
}

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
