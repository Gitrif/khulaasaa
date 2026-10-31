/**
 * Global Modals Controller (Auth/Settings Modal, Sources Modal, Alpha Feedback Modal).
 * Strictly under 500 lines. Zero emojis.
 */

function toggleAuthMode(mode) {
  const loginForm = document.getElementById('modalLoginForm');
  const regForm = document.getElementById('modalRegisterForm');
  const loginBtn = document.getElementById('authModeLoginBtn');
  const regBtn = document.getElementById('authModeRegisterBtn');
  const title = document.getElementById('modalAuthTitle');
  const subtitle = document.getElementById('modalAuthSubtitle');

  if (mode === 'register') {
    if (loginForm) loginForm.classList.add('hidden');
    if (regForm) regForm.classList.remove('hidden');
    if (loginBtn) loginBtn.className = 'modal-tab-btn';
    if (regBtn) regBtn.className = 'modal-tab-btn active';
    if (title) title.textContent = 'Create Free Account';
    if (subtitle) subtitle.textContent = 'Use one account for your web profile and verified Telegram/Viber alert channels.';
  } else {
    if (regForm) regForm.classList.add('hidden');
    if (loginForm) loginForm.classList.remove('hidden');
    if (regBtn) regBtn.className = 'modal-tab-btn';
    if (loginBtn) loginBtn.className = 'modal-tab-btn active';
    if (title) title.textContent = 'Sign In to Khulaasaa';
    if (subtitle) subtitle.textContent = 'Sign in to manage your profile, saved items, and connected alert channels.';
  }
}

function switchModalSettingsTab(tab) {
  const tabChannels = document.getElementById('modalTabChannels');
  const tabAlerts = document.getElementById('modalTabAlerts');
  const btnChannels = document.getElementById('tabBtnChannels');
  const btnAlerts = document.getElementById('tabBtnAlerts');

  if (tab === 'alerts') {
    if (tabChannels) tabChannels.classList.add('hidden');
    if (tabAlerts) tabAlerts.classList.remove('hidden');
    if (btnChannels) btnChannels.className = 'modal-tab-btn';
    if (btnAlerts) btnAlerts.className = 'modal-tab-btn active';
  } else {
    if (tabAlerts) tabAlerts.classList.add('hidden');
    if (tabChannels) tabChannels.classList.remove('hidden');
    if (btnAlerts) btnAlerts.className = 'modal-tab-btn';
    if (btnChannels) btnChannels.className = 'modal-tab-btn active';
  }
}

async function openGlobalAlertsModal(preferredTab) {
  const modal = document.getElementById('globalUnifiedModal');
  const loggedOutView = document.getElementById('modalLoggedOutView');
  const loggedInView = document.getElementById('modalLoggedInView');
  if (!modal) return;

  modal.classList.remove('hidden');

  let user = null;
  try {
    const res = await fetch('/api/auth/me');
    const data = await res.json();
    if (data && data.user) user = data.user;
  } catch (e) {}

  if (user) {
    if (loggedOutView) loggedOutView.classList.add('hidden');
    if (loggedInView) loggedInView.classList.remove('hidden');
    populateLoggedInModal(user);
    if (preferredTab === 'viber' || preferredTab === 'telegram') {
      switchModalSettingsTab('channels');
    } else if (preferredTab === 'alerts') {
      switchModalSettingsTab('alerts');
    }
  } else {
    if (loggedInView) loggedInView.classList.add('hidden');
    if (loggedOutView) loggedOutView.classList.remove('hidden');
    if (preferredTab === 'register') {
      toggleAuthMode('register');
    } else {
      toggleAuthMode('login');
    }
  }
}

function closeGlobalAlertsModal() {
  const modal = document.getElementById('globalUnifiedModal');
  if (modal) modal.classList.add('hidden');
}

function populateLoggedInModal(user) {
  const emailEl = document.getElementById('modalUserEmail');
  if (emailEl) emailEl.textContent = user.email || user.full_name || 'Member Account';

  const tgPip = document.getElementById('modalTgStatusPip');
  const tgBadge = document.getElementById('modalTgBadge');
  const tgSubtitle = document.getElementById('modalTgSubtitle');
  const tgUnlinked = document.getElementById('tgUnlinkedActions');
  const tgLinked = document.getElementById('tgLinkedActions');
  const tgChatInfo = document.getElementById('modalTgChatInfo');

  const isTgVerified = Boolean(user.telegram_verified && user.telegram_chat_id);
  if (isTgVerified) {
    if (tgPip) tgPip.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500';
    if (tgBadge) {
      tgBadge.textContent = 'Verified';
      tgBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800';
    }
    if (tgSubtitle) tgSubtitle.textContent = 'Linked to Telegram Chat ID: ' + user.telegram_chat_id;
    if (tgUnlinked) tgUnlinked.classList.add('hidden');
    if (tgLinked) tgLinked.classList.remove('hidden');
    if (tgChatInfo) tgChatInfo.textContent = 'Chat ID: ' + user.telegram_chat_id;
  } else {
    if (tgPip) tgPip.className = 'w-2.5 h-2.5 rounded-full bg-slate-300';
    if (tgBadge) {
      tgBadge.textContent = 'Not Linked';
      tgBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700';
    }
    if (tgSubtitle) tgSubtitle.textContent = 'Connect @khulaasaa_bot';
    if (tgUnlinked) tgUnlinked.classList.remove('hidden');
    if (tgLinked) tgLinked.classList.add('hidden');
  }

  const viberPip = document.getElementById('modalViberStatusPip');
  const viberBadge = document.getElementById('modalViberBadge');
  const viberSubtitle = document.getElementById('modalViberSubtitle');
  const viberUnlinked = document.getElementById('viberUnlinkedActions');
  const viberLinked = document.getElementById('viberLinkedActions');
  const viberIdInfo = document.getElementById('modalViberIdInfo');

  const isViberVerified = Boolean(user.viber_verified && user.viber_user_id);
  if (isViberVerified) {
    if (viberPip) viberPip.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500';
    if (viberBadge) {
      viberBadge.textContent = 'Verified';
      viberBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800';
    }
    if (viberSubtitle) viberSubtitle.textContent = 'Linked to Viber ID: ' + user.viber_user_id;
    if (viberUnlinked) viberUnlinked.classList.add('hidden');
    if (viberLinked) viberLinked.classList.remove('hidden');
    if (viberIdInfo) viberIdInfo.textContent = 'Viber ID: ' + user.viber_user_id;
  } else {
    if (viberPip) viberPip.className = 'w-2.5 h-2.5 rounded-full bg-slate-300';
    if (viberBadge) {
      viberBadge.textContent = 'Not Linked';
      viberBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700';
    }
    if (viberSubtitle) viberSubtitle.textContent = 'Connect Viber Channel';
    if (viberUnlinked) viberUnlinked.classList.remove('hidden');
    if (viberLinked) viberLinked.classList.add('hidden');
  }

  const pBreaking = document.getElementById('prefAlertBreaking');
  const pTenders = document.getElementById('prefAlertTenders');
  const pJobs = document.getElementById('prefAlertJobs');
  const pJanaza = document.getElementById('prefAlertJanaza');
  if (pBreaking) pBreaking.checked = user.alert_breaking !== false;
  if (pTenders) pTenders.checked = user.alert_tenders !== false;
  if (pJobs) pJobs.checked = user.alert_jobs !== false;
  if (pJanaza) pJanaza.checked = user.alert_obituaries !== false;
}

async function handleModalLogin(e) {
  e.preventDefault();
  const identifier = document.getElementById('loginIdentifier').value.trim();
  const password = document.getElementById('loginPassword').value;
  const errEl = document.getElementById('loginErrorMsg');
  const btn = document.getElementById('btnLoginSubmit');
  errEl.classList.add('hidden');
  btn.disabled = true;
  btn.textContent = 'Signing in...';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: identifier, password: password })
    });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      closeGlobalAlertsModal();
      if (typeof refreshGlobalAuthPill === 'function') await refreshGlobalAuthPill();
      const pendingFollow = sessionStorage.getItem('khulaasaa_pending_follow');
      if (pendingFollow) {
        try {
          const pf = JSON.parse(pendingFollow);
          sessionStorage.removeItem('khulaasaa_pending_follow');
          await fetch('/api/follows', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pf)
          });
          window.location.reload();
          return;
        } catch (err2) {}
      }
      const next = sessionStorage.getItem('khulaasaa_auth_next');
      if (next) {
        sessionStorage.removeItem('khulaasaa_auth_next');
        window.location.href = next;
      } else {
        window.location.reload();
      }
    } else {
      errEl.textContent = data.detail || 'Invalid email or password.';
      errEl.classList.remove('hidden');
    }
  } catch (err) {
    errEl.textContent = 'Network error. Please try again.';
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In →';
  }
}

async function handleModalRegister(e) {
  e.preventDefault();
  const full_name = document.getElementById('regFullName').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const phone = document.getElementById('regPhone').value.trim();
  const password = document.getElementById('regPassword').value;
  const errEl = document.getElementById('registerErrorMsg');
  const btn = document.getElementById('btnRegisterSubmit');
  errEl.classList.add('hidden');
  btn.disabled = true;
  btn.textContent = 'Creating account...';

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name: full_name, email: email, phone: phone, password: password })
    });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      closeGlobalAlertsModal();
      if (typeof refreshGlobalAuthPill === 'function') await refreshGlobalAuthPill();
      window.location.reload();
    } else {
      errEl.textContent = data.detail || 'Registration failed.';
      errEl.classList.remove('hidden');
    }
  } catch (err) {
    errEl.textContent = 'Network error. Please try again.';
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Free Account →';
  }
}

function promptAuthForFollow(targetType, targetId, targetTitle) {
  sessionStorage.setItem('khulaasaa_pending_follow', JSON.stringify({
    target_type: targetType,
    target_id: targetId,
    target_title: targetTitle || targetId
  }));
  openGlobalAlertsModal('auth');
}

function openSourcesModal(evt, cardId, headline) {
  if (evt) evt.stopPropagation();
  const dataEl = document.getElementById('sources-data-' + cardId);
  const listEl = document.getElementById('globalSourcesModalList');
  const titleEl = document.getElementById('globalSourcesModalHeadline');
  if (dataEl && listEl) {
    listEl.innerHTML = dataEl.innerHTML;
  }
  if (titleEl && headline) {
    titleEl.textContent = headline;
  }
  const modal = document.getElementById('globalSourcesModal');
  if (modal) modal.classList.remove('hidden');
}

function closeSourcesModal() {
  const modal = document.getElementById('globalSourcesModal');
  if (modal) modal.classList.add('hidden');
}

function openFeedbackModal() {
  const m = document.getElementById('alphaFeedbackModal');
  if (m) m.classList.remove('hidden');
}

function closeFeedbackModal() {
  const m = document.getElementById('alphaFeedbackModal');
  if (m) m.classList.add('hidden');
}

async function handleFeedbackSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('feedbackSubmitBtn');
  const status = document.getElementById('feedbackStatus');
  const msgEl = document.getElementById('feedbackMessage');
  const contactEl = document.getElementById('feedbackContact');

  const payload = {
    feedback_type: 'direct_message',
    message: msgEl.value.trim(),
    contact_info: contactEl.value.trim() || 'Anonymous Visitor',
    page_url: window.location.pathname + window.location.search
  };

  btn.disabled = true;
  btn.textContent = 'Sending...';

  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      status.className = 'mt-2 text-xs py-1.5 px-2.5 rounded bg-emerald-100 text-emerald-800 font-medium';
      status.textContent = 'Thank you! Your message was sent directly to Telegram.';
      status.classList.remove('hidden');
      msgEl.value = '';
      contactEl.value = '';
      setTimeout(function () {
        closeFeedbackModal();
        status.classList.add('hidden');
        btn.disabled = false;
        btn.textContent = 'Send Message';
      }, 2000);
    } else {
      throw new Error(data.detail || 'Failed to submit');
    }
  } catch (err) {
    status.className = 'mt-2 text-xs py-1.5 px-2.5 rounded bg-rose-100 text-rose-800 font-medium';
    status.textContent = 'Submission error. Please try again.';
    status.classList.remove('hidden');
    btn.disabled = false;
    btn.textContent = 'Send Message';
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const urlParams = new URLSearchParams(window.location.search);
  const authAction = urlParams.get('auth');
  if (authAction) {
    openGlobalAlertsModal(authAction === 'register' ? 'register' : 'auth');
  }

  document.querySelectorAll('a[href^="/"]').forEach(function (link) {
    const triggerPrefetch = function () {
      const href = link.getAttribute('href');
      if (href && !href.startsWith('/api') && !document.querySelector('link[rel="prefetch"][href="' + href + '"]')) {
        const prefetchLink = document.createElement('link');
        prefetchLink.rel = 'prefetch';
        prefetchLink.href = href;
        document.head.appendChild(prefetchLink);
      }
    };
    link.addEventListener('mouseenter', triggerPrefetch, { once: true });
    link.addEventListener('touchstart', triggerPrefetch, { passive: true, once: true });
  });
});
