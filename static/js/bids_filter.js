/**
 * Client-side Tenders & Procurement Filter Controller.
 * Handles instant client query matching and advanced modal filtering.
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
