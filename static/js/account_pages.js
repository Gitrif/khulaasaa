/**
 * Account, Channels, Alert Preferences, Following & Subscription Page Controllers.
 * Strictly under 500 lines. Zero emojis.
 */

// 1. Account Profile & Password (/account)
async function handleUpdateProfile(e) {
  e.preventDefault();
  const name = document.getElementById('fullNameInput').value.trim();
  const phone = document.getElementById('phoneInput').value.trim();
  const statusEl = document.getElementById('profileStatus');
  const btn = document.getElementById('saveProfileBtn');

  btn.disabled = true;
  btn.textContent = 'Saving...';
  statusEl.className = 'hidden';

  try {
    const res = await fetch('/api/account/profile', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name: name, phone: phone })
    });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      statusEl.className = 'text-xs py-2 px-3 rounded bg-green-50 text-green-800 border border-green-200 block';
      statusEl.textContent = 'Profile updated successfully.';
      if (typeof refreshGlobalAuthPill === 'function') refreshGlobalAuthPill();
    } else {
      statusEl.className = 'text-xs py-2 px-3 rounded bg-red-50 text-red-800 border border-red-200 block';
      statusEl.textContent = data.detail || 'Failed to update profile.';
    }
  } catch (err) {
    statusEl.className = 'text-xs py-2 px-3 rounded bg-red-50 text-red-800 border border-red-200 block';
    statusEl.textContent = 'Error: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Profile Changes';
  }
}

async function handleChangePassword(e) {
  e.preventDefault();
  const oldPass = document.getElementById('oldPasswordInput').value;
  const newPass = document.getElementById('newPasswordInput').value;
  const confirmPass = document.getElementById('confirmPasswordInput').value;
  const statusEl = document.getElementById('passwordStatus');
  const btn = document.getElementById('changePasswordBtn');

  if (newPass !== confirmPass) {
    statusEl.className = 'text-xs py-2 px-3 rounded bg-red-50 text-red-800 border border-red-200 block';
    statusEl.textContent = 'New passwords do not match.';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Updating...';
  statusEl.className = 'hidden';

  try {
    const res = await fetch('/api/account/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPass, new_password: newPass })
    });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      statusEl.className = 'text-xs py-2 px-3 rounded bg-green-50 text-green-800 border border-green-200 block';
      statusEl.textContent = 'Password changed successfully.';
      document.getElementById('passwordForm').reset();
    } else {
      statusEl.className = 'text-xs py-2 px-3 rounded bg-red-50 text-red-800 border border-red-200 block';
      statusEl.textContent = data.detail || 'Failed to change password.';
    }
  } catch (err) {
    statusEl.className = 'text-xs py-2 px-3 rounded bg-red-50 text-red-800 border border-red-200 block';
    statusEl.textContent = 'Error: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Update Password';
  }
}

// 2. Account Notification Preferences (/account/alerts)
async function handleSavePreferences(e) {
  e.preventDefault();
  const form = document.getElementById('preferencesForm');
  const btn = document.getElementById('saveBtn');
  const statusEl = document.getElementById('saveStatus');

  btn.disabled = true;
  btn.textContent = 'Saving...';
  statusEl.className = 'hidden';

  const freqEl = form.querySelector('input[name="frequency"]:checked');
  const payload = {
    is_paused: document.getElementById('prefIsPaused').checked ? 1 : 0,
    news_alerts: document.getElementById('prefNewsAlerts').checked ? 1 : 0,
    tender_alerts: document.getElementById('prefTenderAlerts').checked ? 1 : 0,
    job_alerts: document.getElementById('prefJobAlerts').checked ? 1 : 0,
    rental_alerts: document.getElementById('prefRentalAlerts').checked ? 1 : 0,
    breaking_alerts: document.getElementById('prefBreakingAlerts').checked ? 1 : 0,
    followed_content_alerts: document.getElementById('prefFollowedAlerts').checked ? 1 : 0,
    telegram_enabled: document.getElementById('prefTelegramEnabled').checked ? 1 : 0,
    viber_enabled: document.getElementById('prefViberEnabled').checked ? 1 : 0,
    frequency: freqEl ? freqEl.value : 'instant',
    quiet_hours_enabled: document.getElementById('prefQuietEnabled').checked ? 1 : 0,
    quiet_hours_start: document.getElementById('quietStart').value || '23:00',
    quiet_hours_end: document.getElementById('quietEnd').value || '07:00',
    timezone: document.getElementById('timezone').value.trim() || 'Indian/Maldives',
  };

  try {
    const res = await fetch('/api/account/preferences', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      statusEl.className = 'text-xs py-2.5 px-3.5 rounded bg-green-50 text-green-800 border border-green-200 block';
      statusEl.textContent = 'Notification preferences successfully saved.';
      setTimeout(() => { statusEl.className = 'hidden'; }, 3000);
    } else {
      statusEl.className = 'text-xs py-2.5 px-3.5 rounded bg-red-50 text-red-800 border border-red-200 block';
      statusEl.textContent = data.detail || 'Failed to save preferences.';
    }
  } catch (err) {
    statusEl.className = 'text-xs py-2.5 px-3.5 rounded bg-red-50 text-red-800 border border-red-200 block';
    statusEl.textContent = 'Error: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Notification Preferences';
  }
}

// 3. Account Channel Linking (/account/channels)
async function initiateTelegramLink() {
  const btn = document.getElementById('btnConnectTelegram');
  btn.disabled = true;
  btn.textContent = 'Generating link...';

  try {
    const res = await fetch('/api/channels/telegram/token', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      const area = document.getElementById('telegramLinkArea');
      const deepBtn = document.getElementById('telegramDeepLinkBtn');
      const codeSpan = document.getElementById('telegramTokenCode');
      deepBtn.href = data.deep_link;
      codeSpan.textContent = '/link ' + data.token;
      area.classList.remove('hidden');
      btn.classList.add('hidden');
      window.open(data.deep_link, '_blank');
    } else {
      showStatus(data.detail || 'Failed to generate Telegram token', true);
      btn.disabled = false;
      btn.textContent = 'Connect via Telegram Bot';
    }
  } catch (err) {
    showStatus('Error: ' + err.message, true);
    btn.disabled = false;
    btn.textContent = 'Connect via Telegram Bot';
  }
}

async function initiateViberLink() {
  const btn = document.getElementById('btnConnectViber');
  btn.disabled = true;
  btn.textContent = 'Generating PIN...';

  try {
    const res = await fetch('/api/channels/viber/token', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      const area = document.getElementById('viberLinkArea');
      const pinDisp = document.getElementById('viberPinDisplay');
      pinDisp.textContent = data.token;
      area.classList.remove('hidden');
      btn.classList.add('hidden');
    } else {
      showStatus(data.detail || 'Failed to generate Viber PIN', true);
      btn.disabled = false;
      btn.textContent = 'Generate 6-Digit Viber PIN';
    }
  } catch (err) {
    showStatus('Error: ' + err.message, true);
    btn.disabled = false;
    btn.textContent = 'Generate 6-Digit Viber PIN';
  }
}

async function disconnectChannel(channel) {
  if (!confirm('Are you sure you want to disconnect ' + channel.toUpperCase() + '?')) return;
  try {
    const res = await fetch('/api/channels/' + channel + '/disconnect', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showStatus(channel.toUpperCase() + ' disconnected successfully.', false);
      setTimeout(() => window.location.reload(), 800);
    } else {
      showStatus(data.detail || 'Failed to disconnect ' + channel, true);
    }
  } catch (err) {
    showStatus('Error: ' + err.message, true);
  }
}

async function sendTestAlert(channel, targetId) {
  try {
    const res = await fetch('/api/alerts/test-connection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel: channel, target_id: targetId })
    });
    const data = await res.json();
    if (res.ok && data.ok) {
      showStatus('Test alert sent to ' + channel.toUpperCase() + ' successfully.', false);
    } else {
      showStatus(data.detail || 'Failed to deliver test alert.', true);
    }
  } catch (err) {
    showStatus('Error: ' + err.message, true);
  }
}

function showStatus(msg, isError) {
  const el = document.getElementById('channelActionStatus');
  if (!el) return;
  el.className = isError
    ? 'text-xs py-2.5 px-3.5 rounded bg-red-50 text-red-800 border border-red-200 block'
    : 'text-xs py-2.5 px-3.5 rounded bg-green-50 text-green-800 border border-green-200 block';
  el.textContent = msg;
  setTimeout(() => { el.className = 'hidden'; }, 4000);
}

// 4. Following Management (/following)
async function removeFollowCard(targetType, targetId) {
  if (!confirm('Unfollow ' + targetType + ' ' + targetId + '?')) return;
  try {
    const res = await fetch('/api/follows?target_type=' + encodeURIComponent(targetType) + '&target_id=' + encodeURIComponent(targetId), {
      method: 'DELETE'
    });
    const data = await res.json();
    if (data.status === 'ok') {
      const card = document.getElementById('follow-item-' + targetType + '-' + targetId);
      if (card) {
        card.style.opacity = '0';
        setTimeout(() => card.remove(), 250);
      }
      if (data.counts) {
        const totalEl = document.getElementById('countTotal');
        const storiesEl = document.getElementById('countStories');
        const topicsEl = document.getElementById('countTopics');
        const sourcesEl = document.getElementById('countSources');
        if (totalEl) totalEl.textContent = data.counts.total || 0;
        if (storiesEl) storiesEl.textContent = data.counts.story || 0;
        if (topicsEl) topicsEl.textContent = data.counts.topic || 0;
        if (sourcesEl) sourcesEl.textContent = data.counts.source || 0;
      }
    }
  } catch (err) {
    alert('Failed to unfollow: ' + err.message);
  }
}

// 5. Public Alerts Setup Page (/alerts)
async function testPageAlert(channel) {
  const targetId = channel === 'telegram'
    ? document.getElementById('pageChatId').value.trim()
    : document.getElementById('pageViberId').value.trim();

  if (!targetId) {
    alert('Please enter your ' + (channel === 'telegram' ? 'Telegram Chat ID' : 'Viber ID') + ' first.');
    return;
  }
  try {
    const res = await fetch('/api/alerts/test-connection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel: channel, target_id: targetId })
    });
    const data = await res.json();
    if (res.ok && data.ok) {
      alert(data.message || 'Test alert delivered successfully!');
    } else {
      alert(data.detail || 'Could not deliver test alert. Please verify your ID.');
    }
  } catch (err) {
    alert('Error sending test alert: ' + err.message);
  }
}

async function savePagePreferences(e) {
  e.preventDefault();
  const btn = document.getElementById('pageSaveBtn');
  const status = document.getElementById('pageSaveStatus');
  btn.disabled = true;
  btn.innerText = 'Saving...';
  status.classList.add('hidden');

  const chatId = document.getElementById('pageChatId').value.trim();
  const viberId = document.getElementById('pageViberId').value.trim();

  const tDisc = [];
  document.querySelectorAll('input[name="page_tdisc"]:checked').forEach(el => tDisc.push(el.value));
  const tSrc = [];
  document.querySelectorAll('input[name="page_tsrc"]:checked').forEach(el => tSrc.push(el.value));

  const jCat = [];
  document.querySelectorAll('input[name="page_jcat"]:checked').forEach(el => jCat.push(el.value));
  const jSrc = [];
  document.querySelectorAll('input[name="page_jsrc"]:checked').forEach(el => jSrc.push(el.value));

  const isEnabled = document.getElementById('pageTendersEnabled').checked || document.getElementById('pageJobsEnabled').checked;

  try {
    const resp = await fetch('/api/user/alert-settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_chat_id: chatId,
        viber_user_id: viberId,
        tender_alert_disciplines: tDisc.length ? tDisc : ['All'],
        tender_alert_sources: tSrc.length ? tSrc : ['all'],
        job_alert_categories: jCat.length ? jCat : ['all'],
        job_alert_sources: jSrc.length ? jSrc : ['all'],
        alerts_enabled: isEnabled
      })
    });
    const data = await resp.json();
    if (resp.ok && data.status === 'ok') {
      status.innerText = 'Alert preferences saved successfully!';
      status.classList.remove('hidden');
      if (chatId) localStorage.setItem('khulaasaa_tg_connected', '1');
      if (viberId) localStorage.setItem('khulaasaa_viber_connected', '1');
      if (typeof refreshGlobalAuthPill === 'function') refreshGlobalAuthPill();
    } else if (resp.status === 401) {
      const legacyResp = await fetch('/api/alerts/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          tenders: true,
          disciplines: tDisc,
          keywords: tSrc.concat(jCat)
        })
      });
      const legacyData = await legacyResp.json();
      if (legacyResp.ok && legacyData.ok) {
        status.innerText = 'Preferences saved for Telegram chat ' + chatId + '! (Tip: Sign in to sync across devices)';
        status.classList.remove('hidden');
      } else {
        alert('Please sign in to save preferences.');
        if (typeof openGlobalAlertsModal === 'function') openGlobalAlertsModal('auth');
      }
    } else {
      alert(data.detail || 'Failed to save preferences.');
    }
  } catch (err) {
    alert('Error connecting to server: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = 'Save Alert Preferences';
  }
}

// 6. Subscription Plan Selection (/subscription)
function selectPlan(planKey) {
  const sel = document.getElementById('planTierSelect');
  if (sel) {
    sel.value = planKey;
  }
  const formSection = document.getElementById('subscription-form-section');
  if (formSection) {
    formSection.scrollIntoView({ behavior: 'smooth' });
  }
}
