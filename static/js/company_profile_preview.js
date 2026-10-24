function renderProfilePreview() {
  readFormIntoState();
  const container = document.getElementById("corporatePaper");
  if (!container) return;

  const cp = companyProfile;

  container.innerHTML = `
    <!-- PAGE 1: COVER PAGE -->
    <div class="page-sheet p-12 sm:p-16 flex flex-col justify-between relative overflow-hidden" style="background: linear-gradient(135deg, #0A2540 0%, #0070BA 50%, #00A699 100%); color: white;">
      <!-- Subtle geometric wave overlay -->
      <div class="absolute inset-0 opacity-15 pointer-events-none" style="background-image: radial-gradient(#fff 1px, transparent 1px); background-size: 24px 24px;"></div>
      
      <div class="relative z-10 flex justify-between items-start">
        <div class="text-3xl font-serif-display font-black tracking-widest text-white uppercase border-b-2 border-white/40 pb-2">
          ${escapeHtml(cp.company_name)}
        </div>
        <div class="text-right text-xs tracking-widest text-white/80 font-mono">
          | COMPANY PROFILE ${escapeHtml(cp.year)} |
        </div>
      </div>

      <div class="relative z-10 my-auto text-center py-20">
        <div class="text-xs uppercase tracking-[0.3em] font-bold text-teal-200 mb-3">${cp.entity_type === 'international' ? 'International Bidder &amp; Contractor Portfolio' : 'Tender &amp; Vendor Qualification Document'}</div>
        <h1 class="text-5xl sm:text-6xl font-serif-display font-bold tracking-tight text-white mb-6">
          COMPANY PROFILE
        </h1>
        <div class="w-24 h-1 bg-white/60 mx-auto mb-6"></div>
        <p class="max-w-md mx-auto text-sm text-teal-100 font-light leading-relaxed">
          ${escapeHtml(cp.tagline)}
        </p>
      </div>

      <div class="relative z-10 border-t border-white/20 pt-6 flex flex-wrap justify-between items-end text-xs text-teal-100 font-mono">
        <div>
          ${cp.entity_type === 'international' ? `
            <div class="font-bold text-white uppercase">International Bidder (${escapeHtml(cp.country_of_origin || 'Foreign')})</div>
            <div>FOREIGN REG: ${escapeHtml(cp.foreign_reg_no || cp.registration_number)}</div>
            <div>TAX ID: ${escapeHtml(cp.foreign_tax_id || cp.tin_number)}</div>
            ${cp.local_agent_name ? `<div class="text-[11px] text-teal-200">LOCAL AGENT: ${escapeHtml(cp.local_agent_name)} (${escapeHtml(cp.local_agent_reg || 'MED')})</div>` : ''}
          ` : `
            <div>MED REG: ${escapeHtml(cp.registration_number)}</div>
            <div>MIRA TIN: ${escapeHtml(cp.tin_number)}</div>
            <div>JURISDICTION: MALDIVES</div>
          `}
        </div>
        <div class="text-right">
          <div>${escapeHtml(cp.registered_address)}</div>
          <div>${escapeHtml(cp.email)} &bull; ${escapeHtml(cp.phone)}</div>
          ${cp.entity_type === 'international' && cp.local_agent_phone ? `<div class="text-[11px] text-teal-200">Maldives Rep: ${escapeHtml(cp.local_agent_phone)}</div>` : ''}
        </div>
      </div>
    </div>

    <!-- PAGE 2: CORPORATE REGISTRATION & EXECUTIVE STATEMENT -->
    <div class="page-sheet p-10 sm:p-14 flex flex-col justify-between">
      <div>
        <div class="flex justify-between items-center border-b border-hairline pb-3 mb-8 text-xs text-slate">
          <span class="font-bold text-ink uppercase tracking-wider">${escapeHtml(cp.company_name)}</span>
          <span class="font-mono">| COMPANY PROFILE ${escapeHtml(cp.year)} | Page 1 of 4</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-12 gap-8">
          <!-- Left: Foreword Message -->
          <div class="md:col-span-7 space-y-4">
            <h2 class="text-xl font-serif-display font-bold text-ink">Executive Foreword</h2>
            <div class="w-12 h-0.5 bg-lagoon"></div>
            <p class="text-xs text-slate leading-relaxed italic">
              "${escapeHtml(cp.managing_director_message)}"
            </p>
            <div class="pt-2">
              <div class="font-bold text-sm text-ink">${escapeHtml(cp.managing_director_name)}</div>
              <div class="text-xs text-lagoon font-medium">Managing Director</div>
            </div>

            <!-- Corporate Philosophy -->
            <div class="pt-4 border-t border-hairline space-y-2">
              <h3 class="font-bold text-sm text-ink">Our Philosophy</h3>
              <p class="text-xs text-slate leading-relaxed">
                ${escapeHtml(cp.philosophy)}
              </p>
            </div>

            <!-- Corporate Mission -->
            <div class="space-y-2">
              <h3 class="font-bold text-sm text-ink">Our Mission</h3>
              <p class="text-xs text-slate leading-relaxed">
                ${escapeHtml(cp.mission)}
              </p>
            </div>
          </div>

          <!-- Right: Official Registration Box (Gazette Tender Essential) -->
          <div class="md:col-span-5 bg-paper-soft/40 border border-hairline p-5 rounded-lg space-y-3">
            <div class="text-xs font-bold uppercase tracking-wider text-lagoon border-b border-hairline pb-2 flex items-center justify-between">
              <span>${cp.entity_type === 'international' ? 'International Bidder Registry' : 'Official Company Registry'}</span>
              <span class="text-[10px] px-1.5 py-0.2 rounded font-bold ${cp.entity_type === 'international' ? 'bg-amber-100 text-amber-900' : 'bg-emerald-100 text-emerald-900'}">${cp.entity_type === 'international' ? 'Overseas / ICB' : 'Maldives MED'}</span>
            </div>
            
            <div class="space-y-2 text-xs">
              <div>
                <span class="text-slate block text-[11px]">Registered Name:</span>
                <span class="font-bold text-ink">${escapeHtml(cp.company_name)}</span>
              </div>

              ${cp.entity_type === 'international' ? `
              <div>
                <span class="text-slate block text-[11px]">Country of Origin:</span>
                <span class="font-bold text-ink">${escapeHtml(cp.country_of_origin)}</span>
              </div>

              <div>
                <span class="text-slate block text-[11px]">Foreign Registration No:</span>
                <span class="font-mono font-bold text-lagoon text-sm">${escapeHtml(cp.foreign_reg_no || cp.registration_number)}</span>
              </div>

              <div>
                <span class="text-slate block text-[11px]">Home Tax ID / VAT:</span>
                <span class="font-mono font-bold text-ink">${escapeHtml(cp.foreign_tax_id || cp.tin_number)}</span>
              </div>

              <div>
                <span class="text-slate block text-[11px]">Head Office Address:</span>
                <span class="text-ink leading-tight block">${escapeHtml(cp.registered_address)}</span>
              </div>

              <div class="pt-2 border-t border-hairline/80 space-y-1">
                <span class="text-slate block text-[11px] font-bold uppercase tracking-wider text-lagoon">Local Maldivian Representative</span>
                <div><span class="text-slate">Partner / Agent:</span> <strong class="text-ink">${escapeHtml(cp.local_agent_name || 'Direct International Bidder')}</strong></div>
                ${cp.local_agent_reg ? `<div><span class="text-slate">Agent MED Reg:</span> <span class="font-mono font-bold text-ink">${escapeHtml(cp.local_agent_reg)}</span></div>` : ''}
                ${cp.local_agent_phone ? `<div><span class="text-slate">Local Contact:</span> <span class="text-ink">${escapeHtml(cp.local_agent_phone)} &bull; ${escapeHtml(cp.local_agent_email)}</span></div>` : ''}
              </div>
              ` : `
              <div>
                <span class="text-slate block text-[11px]">Registration Number:</span>
                <span class="font-mono font-bold text-lagoon text-sm">${escapeHtml(cp.registration_number)}</span>
              </div>

              <div>
                <span class="text-slate block text-[11px]">Registration Date:</span>
                <span class="font-medium text-ink">${escapeHtml(cp.registration_date)}</span>
              </div>

              <div>
                <span class="text-slate block text-[11px]">MIRA TIN Number:</span>
                <span class="font-mono font-bold text-ink">${escapeHtml(cp.tin_number)}</span>
              </div>

              <div>
                <span class="text-slate block text-[11px]">Registered Address:</span>
                <span class="text-ink leading-tight block">${escapeHtml(cp.registered_address)}</span>
              </div>
              `}
            </div>

            <div class="pt-3 border-t border-hairline text-[11px] text-slate leading-snug">
              ${cp.entity_type === 'international' ?
                'International contractor qualified for overseas tender bidding under Maldivian Public Procurement Rules (PPR).' :
                'Verified corporate legal entity registered under the Ministry of Economic Development, Republic of Maldives.'}
            </div>
          </div>
        </div>
      </div>

      <div class="text-center text-[10px] text-slate pt-4 border-t border-hairline">
        ${escapeHtml(cp.company_name)} &bull; ${escapeHtml(cp.website)}
      </div>
    </div>

    <!-- PAGE 3: DIRECTORS, SHAREHOLDERS & CORE BUSINESS -->
    <div class="page-sheet p-10 sm:p-14 flex flex-col justify-between">
      <div>
        <div class="flex justify-between items-center border-b border-hairline pb-3 mb-8 text-xs text-slate">
          <span class="font-bold text-ink uppercase tracking-wider">${escapeHtml(cp.company_name)}</span>
          <span class="font-mono">| COMPANY PROFILE ${escapeHtml(cp.year)} | Page 2 of 4</span>
        </div>

        <!-- Directors Section -->
        <div class="mb-8">
          <h2 class="text-xl font-serif-display font-bold text-ink mb-1">Directors &amp; Key Shareholders</h2>
          <div class="w-12 h-0.5 bg-lagoon mb-4"></div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            ${cp.directors.map(d => `
              <div class="p-4 bg-paper-soft/30 border border-hairline rounded-md text-xs space-y-1.5">
                <div class="font-bold text-ink text-sm">${escapeHtml(d.name)}</div>
                <div class="text-lagoon font-semibold">${escapeHtml(d.role)}</div>
                <div class="text-slate font-mono text-[11px] pt-1">
                  National ID: <b>${escapeHtml(d.nid || 'N/A')}</b> &bull; ${escapeHtml(d.nationality || 'Maldivian')}
                </div>
                <div class="text-slate text-[11px]">
                  Phone: ${escapeHtml(d.phone || '')} &bull; Email: ${escapeHtml(d.email || '')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Core Business Section -->
        <div>
          <h2 class="text-xl font-serif-display font-bold text-ink mb-1">Core Business &amp; Operations</h2>
          <div class="w-12 h-0.5 bg-lagoon mb-4"></div>

          <div class="space-y-4">
            ${cp.core_business.map(b => `
              <div class="p-4 border-l-3 border-lagoon bg-paper-soft/20 text-xs">
                <h3 class="font-bold text-ink text-sm mb-1">${escapeHtml(b.title)}</h3>
                <p class="text-slate leading-relaxed">${escapeHtml(b.desc)}</p>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <div class="text-center text-[10px] text-slate pt-4 border-t border-hairline">
        ${escapeHtml(cp.company_name)} &bull; ${escapeHtml(cp.website)}
      </div>
    </div>

    <!-- PAGE 4: VALUES, CLIENTS & BACK COVER -->
    <div class="page-sheet p-10 sm:p-14 flex flex-col justify-between">
      <div>
        <div class="flex justify-between items-center border-b border-hairline pb-3 mb-8 text-xs text-slate">
          <span class="font-bold text-ink uppercase tracking-wider">${escapeHtml(cp.company_name)}</span>
          <span class="font-mono">| COMPANY PROFILE ${escapeHtml(cp.year)} | Page 3 of 4</span>
        </div>

        <!-- Corporate Values -->
        <div class="mb-8">
          <h2 class="text-xl font-serif-display font-bold text-ink mb-1">Our Corporate Values</h2>
          <div class="w-12 h-0.5 bg-lagoon mb-4"></div>

          <div class="grid grid-cols-2 gap-3 text-xs">
            ${cp.values.map(v => `
              <div class="p-3 border border-hairline rounded bg-paper-soft/30">
                <div class="font-bold text-ink mb-1">${escapeHtml(v.title)}</div>
                <div class="text-slate leading-relaxed text-[11px]">${escapeHtml(v.desc)}</div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Major Clients / References -->
        <div class="mb-8">
          <h2 class="text-xl font-serif-display font-bold text-ink mb-1">Major Clients &amp; References</h2>
          <div class="w-12 h-0.5 bg-lagoon mb-4"></div>

          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            ${cp.clients.map(c => `
              <div class="p-3 border border-hairline rounded text-center bg-white shadow-2xs font-semibold text-xs text-slate-700 flex items-center justify-center min-h-[50px]">
                ${escapeHtml(c)}
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- Legal Backpage Disclaimer -->
      <div class="border-t border-hairline pt-6 text-xs text-slate">
        <div class="flex flex-wrap justify-between gap-4">
          <div>
            <div class="font-bold text-ink">${escapeHtml(cp.company_name)}</div>
            <div class="text-[11px] text-slate">${escapeHtml(cp.registered_address)}</div>
            <div class="text-[11px] text-slate">${escapeHtml(cp.email)} &bull; ${escapeHtml(cp.website)}</div>
          </div>
          <div class="max-w-xs text-right text-[10px] text-slate/80 leading-relaxed">
            &copy; ${escapeHtml(cp.year)} ${escapeHtml(cp.company_name)}. All Rights Reserved. This document contains confidential corporate specifications prepared for gazette tender bids and official partner qualification.
          </div>
        </div>
      </div>
    </div>
  `;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function loadSampleCompanyProfile() {
  companyProfile = {
    company_name: "MAI & EMI INVESTMENTS PVT LTD",
    registration_number: "C04812021",
    registration_date: "19th April 2021",
    tin_number: "1130267",
    registered_address: "G. Sinamale 1 1202, Buruzu Magu, Male' 20112, Maldives",
    phone: "+960 778 1557",
    email: "info@mai-emi.com",
    website: "www.mai-emi.com",
    year: "2026",
    tagline: "We are a Maldivian company established in Sourcing, Imports, Exports, Customs Clearance, Internal Logistics and Consultancy. Our partners value our products and services for excellence and reliability.",
    philosophy: "At MAI & EMI INVESTMENTS we are passionate in seeing the imports and distribution industry in the Maldives Prosper. Our ambition, our vision, is to be 'the best', with regard to our range of products, our skills, our market success, and our reputation.",
    mission: "We bring global and local value to our industry partners so we all succeed together.",
    managing_director_name: "Mohamed Ashraf",
    managing_director_message: "The world is constantly evolving; we live in an increasingly competitive, complex and fast reality. Solutions for an evolving industry: this vision will be our guide in the years ahead. We are always one step ahead in offering highly reliable products and services. Mai & Emi's success would not be possible without the contribution of our partners and clients.",
    directors: [
      {
        name: "MOHAMED ASHRAF",
        role: "Managing Director / Shareholder",
        email: "ashraf@mai-emi.com",
        phone: "+960 778 1557",
        nid: "A094120",
        dob: "21st May 1978",
        nationality: "Maldivian"
      },
      {
        name: "IBRAHIM ARIF",
        role: "Director",
        email: "arif@mai-emi.com",
        phone: "+960 734 8121",
        nid: "A102809",
        dob: "18th November 1983",
        nationality: "Maldivian"
      }
    ],
    core_business: [
      {
        title: "Importation & Distribution",
        desc: "As an island nation with limited resources, Maldives has a high dependency on imported food & beverage products. We source top quality global brands & maintain an active atoll distribution network."
      },
      {
        title: "Logistics Services",
        desc: "Local logistics is intricate in the Maldives with 90% of cargo dependent on sea transport. We provide reliable domestic logistics solutions on contract and on-demand basis."
      },
      {
        title: "Wholesaling & Retailing",
        desc: "Wholesalers look for reliable suppliers with competitive rates. We offer clients a consistent supply of verified, highest-quality products."
      }
    ],
    values: [
      { title: "Ambition", desc: "Continually seeking to improve all elements of our service." },
      { title: "Creative Energy", desc: "Creating new solutions and flexible responses to customer requests." },
      { title: "Transparency", desc: "Clear, sharply defined decision-making and open operations." },
      { title: "Pride & Ethics", desc: "Integrity, honesty, and high moral standards across all operations." }
    ],
    clients: [
      "Soneva",
      "JOALI Maldives",
      "Cora Cora Maldives",
      "Alila Kothaifaru Maldives",
      "Park Hyatt Maldives Hadahaa"
    ]
  };
  populateFormFromState();
  renderProfilePreview();
}

async function saveCompanyProfileToServer() {
  readFormIntoState();
  try {
    const res = await fetch("/api/company-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(companyProfile)
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      alert("Company Profile saved successfully!");
    } else {
      alert("Failed to save company profile.");
    }
  } catch(e) {
    alert("Connection error saving company profile");
  }
}

// Clean Print with sanitized Document Title (so PDF save defaults to Company_Name_Profile_A4.pdf)
function printCompanyProfile() {
  readFormIntoState();
  const originalTitle = document.title;
  const cleanName = (companyProfile.company_name || "Company_Profile").replace(/[^a-zA-Z0-9_\u0780-\u07BF]/g, '_').replace(/_+/g, '_');
  document.title = `${cleanName}_A4_Profile`;

  window.print();

  setTimeout(() => {
    document.title = originalTitle;
  }, 1000);
}

// 1-Click Direct Download to A4 Multi-Page PDF (zero browser headers, footers, or system crumbs)
async function downloadCompanyProfilePdf() {
  readFormIntoState();
  const cleanName = (companyProfile.company_name || "Company_Profile").replace(/[^a-zA-Z0-9_\u0780-\u07BF]/g, '_').replace(/_+/g, '_');
  const filename = `${cleanName}_A4_Profile.pdf`;

  const container = document.getElementById("corporatePaper");
  const btnTop = document.getElementById("btnDownloadProfileTop");
  const btnRight = document.getElementById("btnDownloadProfileRight");
  const origTopText = btnTop ? btnTop.innerHTML : "";
  const origRightText = btnRight ? btnRight.innerHTML : "";

  if (btnTop) btnTop.innerHTML = `<span>Exporting...</span>`;
  if (btnRight) btnRight.innerHTML = `<span>Exporting...</span>`;

  const opt = {
    margin: 0,
    filename: filename,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true, logging: false },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak: { mode: ['css', 'legacy'] }
  };

  try {
    if (window.html2pdf) {
      await html2pdf().set(opt).from(container).save();
    } else {
      printCompanyProfile();
    }
  } catch(err) {
    console.error("PDF generation error, fallback to print:", err);
    printCompanyProfile();
  } finally {
    if (btnTop) btnTop.innerHTML = origTopText;
    if (btnRight) btnRight.innerHTML = origRightText;
  }
}
