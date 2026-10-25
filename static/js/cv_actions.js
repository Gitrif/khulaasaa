function printCv() {
  const d = collectCvData();
  const originalTitle = document.title;
  const cleanName = (d.fullName || "Maldivian_CV").replace(/[^a-zA-Z0-9_\u0780-\u07BF]/g, '_').replace(/_+/g, '_');
  document.title = `${cleanName}_A4_Standard_CV`;

  window.print();

  setTimeout(() => {
    document.title = originalTitle;
  }, 1000);
}

// 1-Click Direct Download to A4 Standard PDF (zero browser headers, footers, or system crumbs)
async function downloadCvPdf() {
  const d = collectCvData();
  const cleanName = (d.fullName || "Maldivian_CV").replace(/[^a-zA-Z0-9_\u0780-\u07BF]/g, '_').replace(/_+/g, '_');
  const filename = `${cleanName}_A4_Standard_CV.pdf`;

  const paper = document.getElementById("cvPaper");
  const btnTop = document.getElementById("btnDownloadCvTop");
  const btnBar = document.getElementById("btnDownloadCvBar");
  const btnRight = document.getElementById("btnDownloadCvRight");
  const origTopText = btnTop ? btnTop.innerHTML : "";
  const origRightText = btnRight ? btnRight.innerHTML : "";

  if (btnTop) btnTop.innerHTML = `<span>Exporting...</span>`;
  if (btnBar) btnBar.innerHTML = `<span>Exporting...</span>`;
  if (btnRight) btnRight.innerHTML = `<span>Exporting...</span>`;

  const opt = {
    margin: [10, 10, 10, 10], // 10mm clean page margin
    filename: filename,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true, logging: false },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  };

  try {
    if (window.html2pdf) {
      await html2pdf().set(opt).from(paper).save();
    } else {
      printCv();
    }
  } catch(err) {
    console.error("PDF generation error, fallback to print:", err);
    printCv();
  } finally {
    if (btnTop) btnTop.innerHTML = origTopText;
    if (btnBar) btnBar.innerHTML = `<svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/></svg><span>Download A4 PDF</span>`;
    if (btnRight) btnRight.innerHTML = origRightText;
  }
}

// Modal Handlers
function openAuthModal(tab = 'login') {
  if (typeof openGlobalAlertsModal === 'function') {
    openGlobalAlertsModal(tab === 'register' ? 'register' : 'login');
    return;
  }
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.remove("hidden");
  switchAuthTab(tab);
}
function closeAuthModal() {
  if (typeof closeGlobalAlertsModal === 'function') {
    closeGlobalAlertsModal();
  }
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.add("hidden");
}

function switchAuthTab(tab) {
  const loginForm = document.getElementById("loginForm");
  const regForm = document.getElementById("registerForm");
  const tabLogin = document.getElementById("tabLogin");
  const tabRegister = document.getElementById("tabRegister");

  if (tab === 'login') {
    loginForm.classList.remove("hidden");
    regForm.classList.add("hidden");
    tabLogin.className = "flex-1 py-2 text-center border-b-2 border-lagoon text-lagoon font-bold cursor-pointer";
    tabRegister.className = "flex-1 py-2 text-center border-b-2 border-transparent text-slate hover:text-ink cursor-pointer";
  } else {
    loginForm.classList.add("hidden");
    regForm.classList.remove("hidden");
    tabRegister.className = "flex-1 py-2 text-center border-b-2 border-lagoon text-lagoon font-bold cursor-pointer";
    tabLogin.className = "flex-1 py-2 text-center border-b-2 border-transparent text-slate hover:text-ink cursor-pointer";
  }
}

function openProModal() {
  document.getElementById("proModal").classList.remove("hidden");
}
function closeProModal() {
  document.getElementById("proModal").classList.add("hidden");
}

function openAlertSettingsModal() {
  document.getElementById("alertModal").classList.remove("hidden");
}
function closeAlertModal() {
  document.getElementById("alertModal").classList.add("hidden");
}

// Auth Handlers
async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById("loginEmail").value;
  const password = document.getElementById("loginPassword").value;
  const errEl = document.getElementById("loginError");
  errEl.classList.add("hidden");

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (res.ok && data.user) {
      window.location.reload();
    } else {
      errEl.textContent = data.detail || "Invalid email or password";
      errEl.classList.remove("hidden");
    }
  } catch(err) {
    errEl.textContent = "Server connection error";
    errEl.classList.remove("hidden");
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const full_name = document.getElementById("regName").value;
  const email = document.getElementById("regEmail").value;
  const password = document.getElementById("regPassword").value;
  const phone = document.getElementById("regPhone").value;
  const telegram_chat_id = document.getElementById("regTelegram").value;
  const viber_user_id = document.getElementById("regViber") ? document.getElementById("regViber").value : "";
  const errEl = document.getElementById("regError");
  errEl.classList.add("hidden");

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name, email, password, phone, telegram_chat_id, viber_user_id })
    });
    const data = await res.json();
    if (res.ok && data.user) {
      window.location.reload();
    } else {
      errEl.textContent = data.detail || "Registration failed";
      errEl.classList.remove("hidden");
    }
  } catch(err) {
    errEl.textContent = "Server connection error";
    errEl.classList.remove("hidden");
  }
}

async function quickDemoLogin(userKey = 'shifau') {
  try {
    const res = await fetch("/api/auth/demo-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_key: userKey })
    });
    if (res.ok) {
      window.location.reload();
    }
  } catch(e) {}
}

async function logoutUser() {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.reload();
}

async function upgradeUserToPro() {
  if (!currentUser) {
    closeProModal();
    openAuthModal('register');
    return;
  }
  try {
    const res = await fetch("/api/user/upgrade", { method: "POST" });
    if (res.ok) {
      userIsPaid = true;
      closeProModal();
      selectTemplate('executive', true);
      alert("Pro activated! You now have cloud CV saving, all 4 designer templates, and VIP job alerts.");
      window.location.reload();
    }
  } catch(e) {}
}

async function saveAlertSettings() {
  const chatId = document.getElementById("alertChatId") ? document.getElementById("alertChatId").value.trim() : "";
  const viberId = document.getElementById("alertViberId") ? document.getElementById("alertViberId").value.trim() : "";
  const checkboxes = document.querySelectorAll('input[name="alert_cat"]:checked');
  const categories = Array.from(checkboxes).map(cb => cb.value);

  try {
    const res = await fetch("/api/user/job-alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        telegram_chat_id: chatId,
        viber_user_id: viberId,
        categories: categories
      })
    });
    if (res.ok) {
      alert("Job alert preferences saved successfully!");
      closeAlertModal();
    } else {
      alert("Failed to save alert preferences. Make sure you are signed in.");
    }
  } catch(e) {
    alert("Connection error");
  }
}

async function sendTestAlert() {
  const chatId = document.getElementById("alertChatId").value.trim();
  if (!chatId) {
    alert("Please enter your Telegram Chat ID first. Tap 'Open Telegram' to find your ID.");
    return;
  }
  try {
    const res = await fetch("/api/jobs/test-alert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId })
    });
    const data = await res.json();
    if (res.ok && data.ok) {
      alert("Test job alert sent to your Telegram! Check your bot messages.");
    } else {
      alert("Alert dispatch note: " + (data.message || data.detail || "Sent or pending bot token"));
    }
  } catch(e) {
    alert("Connection error sending test alert");
  }
}

async function sendTestViberAlert() {
  const viberId = document.getElementById("alertViberId") ? document.getElementById("alertViberId").value.trim() : "";
  if (!viberId) {
    alert("Please enter your Viber User ID first. Tap 'Open Viber Bot' and send /myid to get your ID.");
    return;
  }
  try {
    const res = await fetch("/api/jobs/test-viber-alert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ viber_user_id: viberId })
    });
    const data = await res.json();
    if (res.ok && data.ok) {
      alert("Test job alert sent to your Viber! Check your chat.");
    } else {
      alert("Alert dispatch note: " + (data.message || data.error || data.detail || "Sent or pending Viber delivery"));
    }
  } catch(e) {
    alert("Connection error sending test Viber alert");
  }
}

let currentCvPage = 1;
const totalCvPages = 5;

function goToCvPage(pageNum) {
  if (pageNum < 1 || pageNum > totalCvPages) return;
  currentCvPage = pageNum;

  for (let i = 1; i <= totalCvPages; i++) {
    const pageEl = document.getElementById('cv-page-' + i);
    const tabEl = document.getElementById('step-tab-' + i);
    if (pageEl) {
      if (i === pageNum) {
        pageEl.classList.remove('hidden');
      } else {
        pageEl.classList.add('hidden');
      }
    }
    if (tabEl) {
      if (i === pageNum) {
        tabEl.classList.add('active');
      } else {
        tabEl.classList.remove('active');
      }
    }
  }

  // Smooth scroll editor container to top
  const form = document.getElementById('cvForm');
  if (form) {
    form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

let isMobilePreviewOpen = false;
function toggleMobileCvPreview() {
  const previewCol = document.querySelector('.lg\\:col-span-7');
  const txt = document.getElementById('txtToggleMobilePreview');
  isMobilePreviewOpen = !isMobilePreviewOpen;

  if (previewCol) {
    if (isMobilePreviewOpen) {
      previewCol.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (txt) txt.textContent = 'Edit';
    } else {
      const form = document.getElementById('cvForm');
      if (form) form.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (txt) txt.textContent = 'Preview';
    }
  }
}
