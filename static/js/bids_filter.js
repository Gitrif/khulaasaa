/**
 * Client-side Tenders & Procurement Filter Controller.
 * Handles instant client query matching, advanced modal filtering,
 * and test alert dispatch to connected subscriber endpoints.
 * Strictly under 500 lines. Zero emojis.
 */

function filterCards(query) {
  const q = (query || "").toLowerCase().trim();
  const rows = document.querySelectorAll("#bids-stream .bid-row");
  rows.forEach(row => {
    if (!q) {
      row.style.display = "";
      return;
    }
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(q) ? "" : "none";
  });
}

function openAdvancedFilterModal() {
  const m = document.getElementById("advancedFilterModal");
  if (m) m.classList.remove("hidden");
}

function closeAdvancedFilterModal() {
  const m = document.getElementById("advancedFilterModal");
  if (m) m.classList.add("hidden");
}

function toggleTelegramPanel() {
  const p = document.getElementById("telegram-panel");
  if (p) p.classList.toggle("hidden");
}

async function sendSpecificTenderAlert(noticeId) {
  let chatId = localStorage.getItem("khulaasaa_tg_chat");
  let botToken = localStorage.getItem("khulaasaa_tg_token");

  if (!chatId) {
    toggleTelegramPanel();
    return;
  }

  try {
    const resp = await fetch("/api/alerts/telegram/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, bot_token: botToken, notice_id: noticeId })
    });
    const data = await resp.json();
    if (data.ok) {
      alert("Tender alert successfully sent to Telegram!");
    } else {
      alert("Failed to send alert: " + (data.error || "Unknown error"));
    }
  } catch (err) {
    alert("Error sending tender alert: " + err.message);
  }
}
