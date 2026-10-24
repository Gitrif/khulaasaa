function loadSampleCv(sampleKey) {
  const sample = SAMPLES[sampleKey] || SAMPLES.shifau;
  populateFormFromData(sample);
}

// Populate Form from JSON
function populateFormFromData(d) {
  document.getElementById("inp_fullName").value = d.fullName || "";
  document.getElementById("inp_nationalId").value = d.nationalId || "";
  document.getElementById("inp_dob").value = d.dob || "";
  document.getElementById("inp_sex").value = d.sex || "Male";
  document.getElementById("inp_nationality").value = d.nationality || "Maldivian";
  document.getElementById("inp_address").value = d.address || "";
  document.getElementById("inp_email").value = d.email || "";
  document.getElementById("inp_phone").value = d.phone || "";
  document.getElementById("inp_photoUrl").value = d.photoUrl || "";
  document.getElementById("inp_summary").value = d.summary || "";
  document.getElementById("inp_training").value = d.training || "";

  // Skills
  const skillsContainer = document.getElementById("skillsContainer");
  skillsContainer.innerHTML = "";
  if (Array.isArray(d.skills) && d.skills.length > 0) {
    d.skills.forEach(s => addSkillField(s));
  } else {
    addSkillField();
  }

  // Experience
  const expContainer = document.getElementById("experienceContainer");
  expContainer.innerHTML = "";
  if (Array.isArray(d.experience) && d.experience.length > 0) {
    d.experience.forEach(exp => addExperienceField(exp));
  } else {
    addExperienceField();
  }

  // Education
  const eduContainer = document.getElementById("educationContainer");
  eduContainer.innerHTML = "";
  if (Array.isArray(d.education) && d.education.length > 0) {
    d.education.forEach(edu => addEducationField(edu));
  } else {
    addEducationField();
  }

  // Certifications
  const certContainer = document.getElementById("certificationsContainer");
  certContainer.innerHTML = "";
  if (Array.isArray(d.certifications) && d.certifications.length > 0) {
    d.certifications.forEach(c => addCertificationField(c));
  }

  // Languages
  const langContainer = document.getElementById("languagesContainer");
  langContainer.innerHTML = "";
  if (Array.isArray(d.languages) && d.languages.length > 0) {
    d.languages.forEach(l => addLanguageField(l));
  } else if (d.languages && typeof d.languages === "object") {
    // Migration from old object format { dhivehi: "...", english: "...", other: "..." }
    if (d.languages.dhivehi) addLanguageField({ language: "Dhivehi", proficiency: d.languages.dhivehi });
    if (d.languages.english) addLanguageField({ language: "English", proficiency: d.languages.english });
    if (d.languages.other) addLanguageField({ language: "Other", customLanguage: d.languages.other, proficiency: "Intermediate / Conversational" });
  } else {
    addLanguageField({ language: "Dhivehi", proficiency: "Native / Bilingual (މާދަރީ ބަސް)" });
    addLanguageField({ language: "English", proficiency: "Fluent / Full Professional" });
  }

  // Portfolio
  const portContainer = document.getElementById("portfolioContainer");
  portContainer.innerHTML = "";
  if (Array.isArray(d.portfolio) && d.portfolio.length > 0) {
    d.portfolio.forEach(p => addPortfolioField(p));
  }

  // Referees
  const refContainer = document.getElementById("refereesContainer");
  refContainer.innerHTML = "";
  if (Array.isArray(d.referees) && d.referees.length > 0) {
    d.referees.forEach(r => addRefereeField(r));
  } else if (typeof d.referees === "string" && d.referees.trim()) {
    // Migration from old free-text referee
    addRefereeField({ name: d.referees, designation: "", company: "", contact: "" });
  } else {
    addRefereeField();
  }

  renderLivePreview();
}

// Dynamic Skill row
function addSkillField(val = "") {
  const c = document.getElementById("skillsContainer");
  const row = document.createElement("div");
  row.className = "flex items-center gap-2";
  row.innerHTML = `
    <input type="text" class="skill-input flex-1 px-2.5 py-1.5 border border-hairline rounded focus:outline-none focus:border-ink text-xs" value="${val.replace(/"/g, '&quot;')}" placeholder="e.g. Airport Operations &amp; VIP Coordination">
    <button type="button" onclick="this.parentElement.remove(); renderLivePreview();" class="text-slate hover:text-flag text-xs px-2 cursor-pointer">&times;</button>
  `;
  c.appendChild(row);
  renderLivePreview();
}

// Dynamic Experience block (Separate From & To Dates)
function addExperienceField(exp = {}) {
  const c = document.getElementById("experienceContainer");
  const block = document.createElement("div");
  block.className = "p-3 border border-hairline rounded bg-paper-soft/30 space-y-2 relative";
  const isCurr = exp.isCurrent ?? (!exp.toDate);
  block.innerHTML = `
    <button type="button" onclick="this.parentElement.remove(); renderLivePreview();" class="absolute top-2 right-2 text-slate hover:text-flag text-sm cursor-pointer" title="Remove">&times;</button>
    <div class="grid grid-cols-2 gap-2 text-xs">
      <div>
        <label class="block text-slate mb-0.5 font-medium">Job Title / Designation</label>
        <input type="text" class="exp-role w-full px-2 py-1 border border-hairline rounded font-medium" value="${(exp.role || '').replace(/"/g, '&quot;')}" placeholder="e.g. Cluster Airport Manager">
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">Company / Employer</label>
        <input type="text" class="exp-company w-full px-2 py-1 border border-hairline rounded" value="${(exp.company || '').replace(/"/g, '&quot;')}" placeholder="e.g. Joali Maldives">
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">From Date</label>
        <input type="text" class="exp-from w-full px-2 py-1 border border-hairline rounded" value="${(exp.fromDate || exp.from || '').replace(/"/g, '&quot;')}" placeholder="e.g. June 2023 or 2023">
      </div>
      <div>
        <div class="flex items-center justify-between mb-0.5">
          <label class="text-slate font-medium">To Date</label>
          <label class="inline-flex items-center gap-1 text-[11px] text-lagoon cursor-pointer">
            <input type="checkbox" class="exp-current accent-lagoon" ${isCurr ? 'checked' : ''} onchange="toggleCurrentJob(this)">
            <span>Current Job</span>
          </label>
        </div>
        <input type="text" class="exp-to w-full px-2 py-1 border border-hairline rounded ${isCurr ? 'bg-slate-100 text-slate-400' : ''}" value="${(exp.toDate || exp.to || '').replace(/"/g, '&quot;')}" placeholder="e.g. Oct 2026 or Present" ${isCurr ? 'disabled' : ''}>
      </div>
      <div class="col-span-2">
        <label class="block text-slate mb-0.5 font-medium">Key Responsibilities &amp; Achievements</label>
        <textarea class="exp-desc w-full px-2 py-1 border border-hairline rounded text-xs" rows="3" placeholder="• Directed end-to-end guest operations...">${(exp.description || '')}</textarea>
      </div>
    </div>
  `;
  c.appendChild(block);
  renderLivePreview();
}

function toggleCurrentJob(checkbox) {
  const container = checkbox.closest('.grid');
  const toInput = container.querySelector('.exp-to');
  if (checkbox.checked) {
    toInput.value = "";
    toInput.disabled = true;
    toInput.classList.add('bg-slate-100', 'text-slate-400');
  } else {
    toInput.disabled = false;
    toInput.classList.remove('bg-slate-100', 'text-slate-400');
  }
  renderLivePreview();
}

// Dynamic Education block (Level, Institution, Degree, Grade, Dates)
function addEducationField(edu = {}) {
  const c = document.getElementById("educationContainer");
  const block = document.createElement("div");
  block.className = "p-3 border border-hairline rounded bg-paper-soft/30 space-y-2 relative";

  const levelOptions = EDUCATION_LEVELS.map(lvl => 
    `<option value="${lvl}" ${edu.level === lvl ? 'selected' : ''}>${lvl}</option>`
  ).join("");

  const instOptions = STANDARD_INSTITUTIONS.map(inst =>
    `<option value="${inst}" ${edu.institution === inst ? 'selected' : ''}>${inst}</option>`
  ).join("");

  const isCustomInst = edu.institution === "Other / Overseas University" || (edu.institution && !STANDARD_INSTITUTIONS.includes(edu.institution));
  const isCurr = edu.isCurrent ?? false;

  block.innerHTML = `
    <button type="button" onclick="this.parentElement.remove(); renderLivePreview();" class="absolute top-2 right-2 text-slate hover:text-flag text-sm cursor-pointer" title="Remove">&times;</button>
    <div class="grid grid-cols-2 gap-2 text-xs">
      <div>
        <label class="block text-slate mb-0.5 font-medium">Education Level</label>
        <select class="edu-level w-full px-2 py-1 border border-hairline rounded bg-white">
          ${levelOptions}
        </select>
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">Degree / Course Name</label>
        <input type="text" class="edu-degree w-full px-2 py-1 border border-hairline rounded font-medium" value="${(edu.degree || '').replace(/"/g, '&quot;')}" placeholder="e.g. Bachelor of Business Management">
      </div>
      <div class="col-span-2">
        <label class="block text-slate mb-0.5 font-medium">School / College / University</label>
        <select class="edu-institution w-full px-2 py-1 border border-hairline rounded bg-white" onchange="toggleCustomInstitution(this)">
          ${instOptions}
        </select>
        <input type="text" class="edu-custom-inst w-full px-2 py-1 mt-1 border border-hairline rounded ${isCustomInst ? '' : 'hidden'}" value="${(edu.customInstitution || '').replace(/"/g, '&quot;')}" placeholder="Type School or University Name...">
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">Grade / Classification</label>
        <input type="text" class="edu-grade w-full px-2 py-1 border border-hairline rounded" value="${(edu.grade || '').replace(/"/g, '&quot;')}" placeholder="e.g. Distinction / First Class / Completed">
      </div>
      <div>
        <div class="flex items-center justify-between mb-0.5">
          <label class="text-slate font-medium">Duration (From – To)</label>
          <label class="inline-flex items-center gap-1 text-[11px] text-lagoon cursor-pointer">
            <input type="checkbox" class="edu-current accent-lagoon" ${isCurr ? 'checked' : ''} onchange="toggleCurrentEdu(this)">
            <span>Ongoing</span>
          </label>
        </div>
        <div class="flex items-center gap-1">
          <input type="text" class="edu-from w-1/2 px-2 py-1 border border-hairline rounded" value="${(edu.fromDate || edu.year || '').replace(/"/g, '&quot;')}" placeholder="From">
          <input type="text" class="edu-to w-1/2 px-2 py-1 border border-hairline rounded ${isCurr ? 'bg-slate-100 text-slate-400' : ''}" value="${(edu.toDate || '').replace(/"/g, '&quot;')}" placeholder="To" ${isCurr ? 'disabled' : ''}>
        </div>
      </div>
    </div>
  `;
  c.appendChild(block);
  renderLivePreview();
}

function toggleCustomInstitution(select) {
  const container = select.closest('.col-span-2');
  const customInput = container.querySelector('.edu-custom-inst');
  if (select.value === "Other / Overseas University") {
    customInput.classList.remove('hidden');
    customInput.focus();
  } else {
    customInput.classList.add('hidden');
  }
  renderLivePreview();
}

function toggleCurrentEdu(checkbox) {
  const block = checkbox.closest('.grid');
  const toInput = block.querySelector('.edu-to');
  if (checkbox.checked) {
    toInput.value = "";
    toInput.disabled = true;
    toInput.classList.add('bg-slate-100', 'text-slate-400');
  } else {
    toInput.disabled = false;
    toInput.classList.remove('bg-slate-100', 'text-slate-400');
  }
  renderLivePreview();
}

// Dynamic Certification block
function addCertificationField(cert = {}) {
  const c = document.getElementById("certificationsContainer");
  const block = document.createElement("div");
  block.className = "p-2.5 border border-hairline rounded bg-paper-soft/30 space-y-1.5 relative";
  block.innerHTML = `
    <button type="button" onclick="this.parentElement.remove(); renderLivePreview();" class="absolute top-2 right-2 text-slate hover:text-flag text-sm cursor-pointer" title="Remove">&times;</button>
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
      <div class="col-span-2 sm:col-span-2">
        <label class="block text-slate mb-0.5 font-medium">Certificate / Training Title</label>
        <input type="text" class="cert-title w-full px-2 py-1 border border-hairline rounded font-medium" value="${(cert.title || '').replace(/"/g, '&quot;')}" placeholder="e.g. Maldivian Driving License B1/B2">
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">Issuing Authority</label>
        <input type="text" class="cert-issuer w-full px-2 py-1 border border-hairline rounded" value="${(cert.issuer || '').replace(/"/g, '&quot;')}" placeholder="e.g. Ministry of Transport">
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">Year / Date</label>
        <input type="text" class="cert-year w-full px-2 py-1 border border-hairline rounded" value="${(cert.year || '').replace(/"/g, '&quot;')}" placeholder="e.g. 2023">
      </div>
    </div>
  `;
  c.appendChild(block);
  renderLivePreview();
}

// Dynamic Language block (Select standard from DB + Proficiency)
function addLanguageField(lang = {}) {
  const c = document.getElementById("languagesContainer");
  const block = document.createElement("div");
  block.className = "flex items-center gap-2 p-2 border border-hairline rounded bg-paper-soft/20 text-xs";

  const isOther = lang.language === "Other" || (lang.language && !STANDARD_LANGUAGES.includes(lang.language));
  const currentLang = isOther ? "Other" : (lang.language || "English");

  const langOpts = STANDARD_LANGUAGES.map(l =>
    `<option value="${l}" ${currentLang === l ? 'selected' : ''}>${l}</option>`
  ).join("") + `<option value="Other" ${isOther ? 'selected' : ''}>Other Language...</option>`;

  const profOpts = LANGUAGE_PROFICIENCIES.map(p =>
    `<option value="${p}" ${lang.proficiency === p ? 'selected' : ''}>${p}</option>`
  ).join("");

  block.innerHTML = `
    <select class="lang-select w-36 px-2 py-1 border border-hairline rounded bg-white font-medium" onchange="toggleCustomLanguage(this)">
      ${langOpts}
    </select>
    <input type="text" class="lang-custom w-32 px-2 py-1 border border-hairline rounded ${isOther ? '' : 'hidden'}" value="${(lang.customLanguage || (isOther ? lang.language : '') || '').replace(/"/g, '&quot;')}" placeholder="Language name">
    <select class="lang-prof flex-1 px-2 py-1 border border-hairline rounded bg-white">
      ${profOpts}
    </select>
    <button type="button" onclick="this.parentElement.remove(); renderLivePreview();" class="text-slate hover:text-flag text-xs px-2 cursor-pointer">&times;</button>
  `;
  c.appendChild(block);
  renderLivePreview();
}

function toggleCustomLanguage(select) {
  const customInput = select.parentElement.querySelector('.lang-custom');
  if (select.value === "Other") {
    customInput.classList.remove('hidden');
    customInput.focus();
  } else {
    customInput.classList.add('hidden');
  }
  renderLivePreview();
}

// Dynamic Portfolio block (Pro)
function addPortfolioField(proj = {}) {
  const c = document.getElementById("portfolioContainer");
  const block = document.createElement("div");
  block.className = "p-3 border border-amber-200 bg-amber-50/20 rounded space-y-2 relative text-xs";
  block.innerHTML = `
    <button type="button" onclick="this.parentElement.remove(); renderLivePreview();" class="absolute top-2 right-2 text-slate hover:text-flag text-sm cursor-pointer" title="Remove">&times;</button>
    <div class="grid grid-cols-2 gap-2">
      <div>
        <label class="block text-slate mb-0.5 font-medium">Project / Portfolio Title</label>
        <input type="text" class="proj-title w-full px-2 py-1 border border-hairline rounded font-medium" value="${(proj.title || '').replace(/"/g, '&quot;')}" placeholder="e.g. VIP Seaplane Lounge SOP">
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">Role in Project</label>
        <input type="text" class="proj-role w-full px-2 py-1 border border-hairline rounded" value="${(proj.role || '').replace(/"/g, '&quot;')}" placeholder="e.g. Project Lead / Designer">
      </div>
      <div class="col-span-2">
        <label class="block text-slate mb-0.5 font-medium">Project URL / Link</label>
        <input type="text" class="proj-url w-full px-2 py-1 border border-hairline rounded" value="${(proj.url || '').replace(/"/g, '&quot;')}" placeholder="https://...">
      </div>
      <div class="col-span-2">
        <label class="block text-slate mb-0.5 font-medium">Description</label>
        <textarea class="proj-desc w-full px-2 py-1 border border-hairline rounded" rows="2" placeholder="Briefly describe key accomplishments...">${(proj.description || '')}</textarea>
      </div>
    </div>
  `;
  c.appendChild(block);
  renderLivePreview();
}

// Dynamic Referee block (Separated Name, Designation, Company, Contact)
function addRefereeField(ref = {}) {
  const c = document.getElementById("refereesContainer");
  const block = document.createElement("div");
  block.className = "p-3 border border-hairline rounded bg-paper-soft/30 space-y-2 relative text-xs";
  block.innerHTML = `
    <button type="button" onclick="this.parentElement.remove(); renderLivePreview();" class="absolute top-2 right-2 text-slate hover:text-flag text-sm cursor-pointer" title="Remove">&times;</button>
    <div class="grid grid-cols-2 gap-2">
      <div>
        <label class="block text-slate mb-0.5 font-medium">Referee Full Name</label>
        <input type="text" class="ref-name w-full px-2 py-1 border border-hairline rounded font-medium" value="${(ref.name || '').replace(/"/g, '&quot;')}" placeholder="e.g. Mr. Mohamed Atheef">
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">Designation / Title</label>
        <input type="text" class="ref-desig w-full px-2 py-1 border border-hairline rounded" value="${(ref.designation || '').replace(/"/g, '&quot;')}" placeholder="e.g. Managing Director">
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">Company / Organization</label>
        <input type="text" class="ref-company w-full px-2 py-1 border border-hairline rounded" value="${(ref.company || '').replace(/"/g, '&quot;')}" placeholder="e.g. Wood Apple Pvt Ltd">
      </div>
      <div>
        <label class="block text-slate mb-0.5 font-medium">Contact (Mobile / Email)</label>
        <input type="text" class="ref-contact w-full px-2 py-1 border border-hairline rounded" value="${(ref.contact || '').replace(/"/g, '&quot;')}" placeholder="e.g. +960 772 0258">
      </div>
    </div>
  `;
  c.appendChild(block);
  renderLivePreview();
}

// Photo Upload Handler (Converts file to Base64)
function handlePhotoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(evt) {
    document.getElementById("inp_photoUrl").value = evt.target.result;
    renderLivePreview();
  };
  reader.readAsDataURL(file);
}

function clearPhoto() {
  document.getElementById("inp_photoUrl").value = "";
  const fileInput = document.getElementById("inp_photoFile");
  if (fileInput) fileInput.value = "";
  renderLivePreview();
}

// Gather all current form data
function collectCvData() {
  const skills = Array.from(document.querySelectorAll(".skill-input"))
    .map(el => el.value.trim())
    .filter(Boolean);

  const experience = Array.from(document.querySelectorAll("#experienceContainer > div"))
    .map(block => {
      const isCurrent = block.querySelector(".exp-current") ? block.querySelector(".exp-current").checked : false;
      const fromDate = block.querySelector(".exp-from") ? block.querySelector(".exp-from").value.trim() : "";
      const toDate = isCurrent ? "" : (block.querySelector(".exp-to") ? block.querySelector(".exp-to").value.trim() : "");
      return {
        role: block.querySelector(".exp-role") ? block.querySelector(".exp-role").value.trim() : "",
        company: block.querySelector(".exp-company") ? block.querySelector(".exp-company").value.trim() : "",
        fromDate,
        toDate,
        isCurrent,
        description: block.querySelector(".exp-desc") ? block.querySelector(".exp-desc").value.trim() : ""
      };
    })
    .filter(e => e.role || e.company);

  const education = Array.from(document.querySelectorAll("#educationContainer > div"))
    .map(block => {
      const isCurrent = block.querySelector(".edu-current") ? block.querySelector(".edu-current").checked : false;
      const level = block.querySelector(".edu-level") ? block.querySelector(".edu-level").value : "";
      const instSelect = block.querySelector(".edu-institution");
      const inst = instSelect ? instSelect.value : "";
      const customInst = block.querySelector(".edu-custom-inst") ? block.querySelector(".edu-custom-inst").value.trim() : "";
      const fromDate = block.querySelector(".edu-from") ? block.querySelector(".edu-from").value.trim() : "";
      const toDate = isCurrent ? "" : (block.querySelector(".edu-to") ? block.querySelector(".edu-to").value.trim() : "");

      return {
        level,
        institution: inst,
        customInstitution: customInst,
        degree: block.querySelector(".edu-degree") ? block.querySelector(".edu-degree").value.trim() : "",
        grade: block.querySelector(".edu-grade") ? block.querySelector(".edu-grade").value.trim() : "",
        fromDate,
        toDate,
        isCurrent
      };
    })
    .filter(e => e.degree || e.institution);

  const certifications = Array.from(document.querySelectorAll("#certificationsContainer > div"))
    .map(block => ({
      title: block.querySelector(".cert-title") ? block.querySelector(".cert-title").value.trim() : "",
      issuer: block.querySelector(".cert-issuer") ? block.querySelector(".cert-issuer").value.trim() : "",
      year: block.querySelector(".cert-year") ? block.querySelector(".cert-year").value.trim() : ""
    }))
    .filter(c => c.title);

  const languages = Array.from(document.querySelectorAll("#languagesContainer > div"))
    .map(block => {
      const select = block.querySelector(".lang-select");
      const langVal = select ? select.value : "English";
      const customVal = block.querySelector(".lang-custom") ? block.querySelector(".lang-custom").value.trim() : "";
      const prof = block.querySelector(".lang-prof") ? block.querySelector(".lang-prof").value : "Fluent";
      const resolvedLang = langVal === "Other" && customVal ? customVal : langVal;
      return {
        language: resolvedLang,
        proficiency: prof
      };
    })
    .filter(l => l.language);

  const portfolio = Array.from(document.querySelectorAll("#portfolioContainer > div"))
    .map(block => ({
      title: block.querySelector(".proj-title") ? block.querySelector(".proj-title").value.trim() : "",
      role: block.querySelector(".proj-role") ? block.querySelector(".proj-role").value.trim() : "",
      url: block.querySelector(".proj-url") ? block.querySelector(".proj-url").value.trim() : "",
      description: block.querySelector(".proj-desc") ? block.querySelector(".proj-desc").value.trim() : ""
    }))
    .filter(p => p.title);

  const referees = Array.from(document.querySelectorAll("#refereesContainer > div"))
    .map(block => ({
      name: block.querySelector(".ref-name") ? block.querySelector(".ref-name").value.trim() : "",
      designation: block.querySelector(".ref-desig") ? block.querySelector(".ref-desig").value.trim() : "",
      company: block.querySelector(".ref-company") ? block.querySelector(".ref-company").value.trim() : "",
      contact: block.querySelector(".ref-contact") ? block.querySelector(".ref-contact").value.trim() : ""
    }))
    .filter(r => r.name);

  return {
    fullName: document.getElementById("inp_fullName").value.trim(),
    nationalId: document.getElementById("inp_nationalId").value.trim(),
    dob: document.getElementById("inp_dob").value.trim(),
    sex: document.getElementById("inp_sex").value,
    nationality: document.getElementById("inp_nationality").value.trim(),
    address: document.getElementById("inp_address").value.trim(),
    email: document.getElementById("inp_email").value.trim(),
    phone: document.getElementById("inp_phone").value.trim(),
    photoUrl: document.getElementById("inp_photoUrl").value.trim(),
    summary: document.getElementById("inp_summary").value.trim(),
    skills,
    experience,
    education,
    certifications,
    training: document.getElementById("inp_training").value.trim(),
    languages,
    portfolio,
    referees
  };
}
