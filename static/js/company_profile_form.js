// Server injected profile if available from window
const SERVER_PROFILE = typeof window !== 'undefined' ? (window.companyState || window.SERVER_PROFILE || null) : null;

// Initial Profile State
let companyProfile = SERVER_PROFILE || {
  company_name: "MAI & EMI INVESTMENTS PVT LTD",
  entity_type: "maldivian",
  country_of_origin: "Maldives",
  registration_number: "C04812021",
  registration_date: "19th April 2021",
  tin_number: "1130267",
  foreign_reg_no: "",
  foreign_tax_id: "",
  local_agent_name: "",
  local_agent_reg: "",
  local_agent_phone: "",
  local_agent_email: "",
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

document.addEventListener("DOMContentLoaded", () => {
  populateFormFromState();
  renderProfilePreview();
});

function setEntityType(type) {
  companyProfile.entity_type = type;
  const isMaldives = (type === 'maldivian');
  const secMv = document.getElementById("sectionMaldivesFields");
  const secIntl = document.getElementById("sectionIntlFields");
  const btnMv = document.getElementById("btnEntityMaldives");
  const btnIntl = document.getElementById("btnEntityIntl");

  if (secMv) secMv.style.display = isMaldives ? 'block' : 'none';
  if (secIntl) secIntl.style.display = isMaldives ? 'none' : 'block';

  if (btnMv && btnIntl) {
    if (isMaldives) {
      btnMv.className = "py-1.5 px-3 rounded text-xs font-bold transition flex items-center justify-center gap-1.5 bg-white text-emerald-800 shadow-xs border border-emerald-300";
      btnIntl.className = "py-1.5 px-3 rounded text-xs font-semibold text-slate transition flex items-center justify-center gap-1.5 hover:text-ink";
    } else {
      btnIntl.className = "py-1.5 px-3 rounded text-xs font-bold transition flex items-center justify-center gap-1.5 bg-white text-emerald-800 shadow-xs border border-emerald-300";
      btnMv.className = "py-1.5 px-3 rounded text-xs font-semibold text-slate transition flex items-center justify-center gap-1.5 hover:text-ink";
    }
  }
  renderProfilePreview();
}

function syncYearIntl(val) {
  const yr = document.getElementById("cpYear");
  if (yr) yr.value = val;
  renderProfilePreview();
}

function populateFormFromState() {
  setEntityType(companyProfile.entity_type || 'maldivian');
  document.getElementById("cpName").value = companyProfile.company_name || "";
  document.getElementById("cpRegNo").value = companyProfile.registration_number || "";
  document.getElementById("cpRegDate").value = companyProfile.registration_date || "";
  document.getElementById("cpTin").value = companyProfile.tin_number || "";
  document.getElementById("cpYear").value = companyProfile.year || "2026";
  document.getElementById("cpAddress").value = companyProfile.registered_address || "";

  // International fields
  const cpCountry = document.getElementById("cpCountry");
  if (cpCountry) cpCountry.value = companyProfile.country_of_origin || "Maldives";
  const cpForeignReg = document.getElementById("cpForeignReg");
  if (cpForeignReg) cpForeignReg.value = companyProfile.foreign_reg_no || "";
  const cpForeignTax = document.getElementById("cpForeignTax");
  if (cpForeignTax) cpForeignTax.value = companyProfile.foreign_tax_id || "";
  const cpYearIntl = document.getElementById("cpYearIntl");
  if (cpYearIntl) cpYearIntl.value = companyProfile.year || "2026";
  const cpAddressIntl = document.getElementById("cpAddressIntl");
  if (cpAddressIntl) cpAddressIntl.value = companyProfile.registered_address || "";
  const cpLocalAgentName = document.getElementById("cpLocalAgentName");
  if (cpLocalAgentName) cpLocalAgentName.value = companyProfile.local_agent_name || "";
  const cpLocalAgentReg = document.getElementById("cpLocalAgentReg");
  if (cpLocalAgentReg) cpLocalAgentReg.value = companyProfile.local_agent_reg || "";
  const cpLocalAgentPhone = document.getElementById("cpLocalAgentPhone");
  if (cpLocalAgentPhone) cpLocalAgentPhone.value = companyProfile.local_agent_phone || "";
  const cpLocalAgentEmail = document.getElementById("cpLocalAgentEmail");
  if (cpLocalAgentEmail) cpLocalAgentEmail.value = companyProfile.local_agent_email || "";

  document.getElementById("cpPhone").value = companyProfile.phone || "";
  document.getElementById("cpEmail").value = companyProfile.email || "";
  document.getElementById("cpWebsite").value = companyProfile.website || "";
  document.getElementById("cpTagline").value = companyProfile.tagline || "";
  document.getElementById("cpPhilosophy").value = companyProfile.philosophy || "";
  document.getElementById("cpMission").value = companyProfile.mission || "";
  document.getElementById("cpMdName").value = companyProfile.managing_director_name || "";
  document.getElementById("cpMdTitle").value = "Managing Director";
  document.getElementById("cpMdMsg").value = companyProfile.managing_director_message || "";

  renderDirectorsForm();
  renderCoreBusinessForm();

  document.getElementById("cpValues").value = (companyProfile.values || []).map(v => v.title).join(", ");
  document.getElementById("cpClients").value = (companyProfile.clients || []).join(", ");
}

function renderDirectorsForm() {
  const container = document.getElementById("directorsContainer");
  container.innerHTML = "";
  companyProfile.directors.forEach((d, idx) => {
    const card = document.createElement("div");
    card.className = "p-3 bg-paper-soft/40 border border-hairline rounded relative space-y-2 text-xs";
    card.innerHTML = `
      <div class="flex items-center justify-between font-bold text-ink">
        <span>Director / Shareholder #${idx + 1}</span>
        ${companyProfile.directors.length > 1 ? `<button type="button" onclick="removeDirector(${idx})" class="text-flag hover:underline text-[11px]">Remove</button>` : ''}
      </div>
      <div class="grid grid-cols-2 gap-2">
        <input type="text" value="${escapeHtml(d.name)}" oninput="updateDirector(${idx}, 'name', this.value)" placeholder="Full Name" class="px-2 py-1.5 border border-hairline rounded bg-white">
        <input type="text" value="${escapeHtml(d.role)}" oninput="updateDirector(${idx}, 'role', this.value)" placeholder="Designation" class="px-2 py-1.5 border border-hairline rounded bg-white">
      </div>
      <div class="grid grid-cols-3 gap-2">
        <input type="text" value="${escapeHtml(d.nid)}" oninput="updateDirector(${idx}, 'nid', this.value)" placeholder="National ID (e.g. A094120)" class="px-2 py-1.5 border border-hairline rounded bg-white font-mono">
        <input type="text" value="${escapeHtml(d.phone)}" oninput="updateDirector(${idx}, 'phone', this.value)" placeholder="Phone" class="px-2 py-1.5 border border-hairline rounded bg-white">
        <input type="text" value="${escapeHtml(d.email)}" oninput="updateDirector(${idx}, 'email', this.value)" placeholder="Email" class="px-2 py-1.5 border border-hairline rounded bg-white">
      </div>
    `;
    container.appendChild(card);
  });
}

function renderCoreBusinessForm() {
  const container = document.getElementById("coreBusinessContainer");
  container.innerHTML = "";
  companyProfile.core_business.forEach((b, idx) => {
    const card = document.createElement("div");
    card.className = "p-3 bg-paper-soft/40 border border-hairline rounded relative space-y-2 text-xs";
    card.innerHTML = `
      <div class="flex items-center justify-between font-bold text-ink">
        <span>Service Line #${idx + 1}</span>
        ${companyProfile.core_business.length > 1 ? `<button type="button" onclick="removeCoreBusiness(${idx})" class="text-flag hover:underline text-[11px]">Remove</button>` : ''}
      </div>
      <input type="text" value="${escapeHtml(b.title)}" oninput="updateCoreBusiness(${idx}, 'title', this.value)" placeholder="Service / Business Title" class="w-full px-2 py-1.5 border border-hairline rounded bg-white font-semibold">
      <textarea rows="2" oninput="updateCoreBusiness(${idx}, 'desc', this.value)" placeholder="Service description &amp; capabilities" class="w-full px-2 py-1.5 border border-hairline rounded bg-white">${escapeHtml(b.desc)}</textarea>
    `;
    container.appendChild(card);
  });
}

function addDirectorField() {
  companyProfile.directors.push({
    name: "",
    role: "Director",
    email: "",
    phone: "+960 ",
    nid: "",
    dob: "",
    nationality: "Maldivian"
  });
  renderDirectorsForm();
  renderProfilePreview();
}

function removeDirector(idx) {
  companyProfile.directors.splice(idx, 1);
  renderDirectorsForm();
  renderProfilePreview();
}

function updateDirector(idx, field, val) {
  companyProfile.directors[idx][field] = val;
  renderProfilePreview();
}

function addCoreBusinessField() {
  companyProfile.core_business.push({
    title: "",
    desc: ""
  });
  renderCoreBusinessForm();
  renderProfilePreview();
}

function removeCoreBusiness(idx) {
  companyProfile.core_business.splice(idx, 1);
  renderCoreBusinessForm();
  renderProfilePreview();
}

function updateCoreBusiness(idx, field, val) {
  companyProfile.core_business[idx][field] = val;
  renderProfilePreview();
}

function readFormIntoState() {
  companyProfile.company_name = document.getElementById("cpName").value.trim() || "MAI & EMI INVESTMENTS PVT LTD";
  const isMaldives = (companyProfile.entity_type !== 'international');

  if (isMaldives) {
    companyProfile.country_of_origin = "Maldives";
    companyProfile.registration_number = document.getElementById("cpRegNo").value.trim();
    companyProfile.registration_date = document.getElementById("cpRegDate").value.trim();
    companyProfile.tin_number = document.getElementById("cpTin").value.trim();
    companyProfile.year = document.getElementById("cpYear").value.trim() || "2026";
    companyProfile.registered_address = document.getElementById("cpAddress").value.trim();
  } else {
    const cpCountry = document.getElementById("cpCountry");
    const cpForeignReg = document.getElementById("cpForeignReg");
    const cpForeignTax = document.getElementById("cpForeignTax");
    const cpYearIntl = document.getElementById("cpYearIntl");
    const cpAddressIntl = document.getElementById("cpAddressIntl");
    const cpLocalAgentName = document.getElementById("cpLocalAgentName");
    const cpLocalAgentReg = document.getElementById("cpLocalAgentReg");
    const cpLocalAgentPhone = document.getElementById("cpLocalAgentPhone");
    const cpLocalAgentEmail = document.getElementById("cpLocalAgentEmail");

    companyProfile.country_of_origin = cpCountry ? cpCountry.value.trim() : "Overseas";
    companyProfile.foreign_reg_no = cpForeignReg ? cpForeignReg.value.trim() : "";
    companyProfile.foreign_tax_id = cpForeignTax ? cpForeignTax.value.trim() : "";
    companyProfile.registration_number = companyProfile.foreign_reg_no || "INTL-REG";
    companyProfile.tin_number = companyProfile.foreign_tax_id || "INTL-TAX";
    companyProfile.year = (cpYearIntl && cpYearIntl.value.trim()) || "2026";
    companyProfile.registered_address = cpAddressIntl ? cpAddressIntl.value.trim() : "";
    companyProfile.local_agent_name = cpLocalAgentName ? cpLocalAgentName.value.trim() : "";
    companyProfile.local_agent_reg = cpLocalAgentReg ? cpLocalAgentReg.value.trim() : "";
    companyProfile.local_agent_phone = cpLocalAgentPhone ? cpLocalAgentPhone.value.trim() : "";
    companyProfile.local_agent_email = cpLocalAgentEmail ? cpLocalAgentEmail.value.trim() : "";
  }

  companyProfile.phone = document.getElementById("cpPhone").value.trim();
  companyProfile.email = document.getElementById("cpEmail").value.trim();
  companyProfile.website = document.getElementById("cpWebsite").value.trim();
  companyProfile.tagline = document.getElementById("cpTagline").value.trim();
  companyProfile.philosophy = document.getElementById("cpPhilosophy").value.trim();
  companyProfile.mission = document.getElementById("cpMission").value.trim();
  companyProfile.managing_director_name = document.getElementById("cpMdName").value.trim();
  companyProfile.managing_director_message = document.getElementById("cpMdMsg").value.trim();

  const rawVals = document.getElementById("cpValues").value.split(",");
  companyProfile.values = rawVals.map(v => ({ title: v.trim(), desc: "Commitment to excellence and ethical standards." })).filter(v => v.title);

  const rawClients = document.getElementById("cpClients").value.split(",");
  companyProfile.clients = rawClients.map(c => c.trim()).filter(Boolean);
}

