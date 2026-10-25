// Format Date Range Helper: "June 2023 – Present" or "2018 – 2025"
function formatDateRange(fromDate, toDate, isCurrent) {
  if (!fromDate && !toDate) return "";
  if (isCurrent || !toDate) {
    return `${fromDate || ''} – Present`;
  }
  return `${fromDate} – ${toDate}`;
}

// =====================================================================
// LIVE CV PREVIEW RENDERERS FOR 4 TEMPLATES
// =====================================================================

function renderLivePreview() {
  const d = collectCvData();
  const paper = document.getElementById("cvPaper");
  if (!paper) return;

  const tmpl = currentTemplate || 'standard';
  paper.className = "cv-paper cv-theme-" + tmpl;

  if (tmpl === 'executive') {
    paper.innerHTML = renderExecutiveTemplate(d);
  } else if (tmpl === 'modern') {
    paper.innerHTML = renderModernTemplate(d);
  } else if (tmpl === 'technical') {
    paper.innerHTML = renderTechnicalTemplate(d);
  } else {
    paper.innerHTML = renderStandardTemplate(d);
  }
}

// 1. STANDARD MALDIVIAN TEMPLATE (Free Default)
function renderStandardTemplate(d) {
  // Photo rendering rule: IF NO PHOTO, DO NOT PRINT PLACEHOLDER BOX
  const photoHtml = d.photoUrl ? `
    <div class="cv-std-photo">
      <img src="${d.photoUrl}" alt="${d.fullName}">
    </div>
  ` : '';

  // Demographics Bar
  const demographicsHtml = `
    <div class="cv-std-demographics">
      <span><b>Sex:</b> ${d.sex || 'Male'}</span>
      <span class="sep">|</span>
      <span><b>DOB:</b> ${d.dob || '—'}</span>
      <span class="sep">|</span>
      <span><b>Nationality:</b> ${d.nationality || 'Maldivian'}</span>
      <span class="sep">|</span>
      <span><b>National ID#:</b> <b class="font-mono">${d.nationalId || '—'}</b></span>
    </div>
  `;

  // Experience List
  let expHtml = '';
  if (d.experience && d.experience.length > 0) {
    const items = d.experience.map(e => `
      <div class="cv-std-item">
        <div class="cv-std-item-header">
          <span>${e.role || 'Designation'} ${e.company ? '– ' + e.company : ''}</span>
          <span class="cv-std-date">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
        </div>
        ${e.description ? `<div class="cv-std-desc">${e.description}</div>` : ''}
      </div>
    `).join('');
    expHtml = `
      <div class="cv-std-section">
        <h2 class="cv-std-heading">Experience</h2>
        <div>${items}</div>
      </div>
    `;
  }

  // Education List
  let eduHtml = '';
  if (d.education && d.education.length > 0) {
    const items = d.education.map(e => {
      const instName = (e.institution === "Other / Overseas University" && e.customInstitution) ? e.customInstitution : e.institution;
      return `
        <div class="cv-std-item">
          <div class="cv-std-item-header">
            <span>${e.degree || e.level} ${instName ? '– ' + instName : ''} ${e.grade ? '(' + e.grade + ')' : ''}</span>
            <span class="cv-std-date">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
          </div>
        </div>
      `;
    }).join('');
    eduHtml = `
      <div class="cv-std-section">
        <h2 class="cv-std-heading">Education &amp; Qualifications</h2>
        <div>${items}</div>
      </div>
    `;
  }

  // Certifications
  let certHtml = '';
  if ((d.certifications && d.certifications.length > 0) || d.training) {
    const certList = (d.certifications || []).map(c => `
      <div class="cv-std-item-header">• ${c.title} ${c.issuer ? '– ' + c.issuer : ''} ${c.year ? '(' + c.year + ')' : ''}</div>
    `).join('');
    certHtml = `
      <div class="cv-std-section">
        <h2 class="cv-std-heading">Other Training &amp; Certifications</h2>
        <div>
          ${certList}
          ${d.training ? `<div class="cv-std-desc">${d.training}</div>` : ''}
        </div>
      </div>
    `;
  }

  // Languages
  let langHtml = '';
  if (d.languages && d.languages.length > 0) {
    const langItems = d.languages.map(l => `<div>• <b>${l.language}:</b> ${l.proficiency}</div>`).join('');
    langHtml = `
      <div class="cv-std-section">
        <h2 class="cv-std-heading">Languages</h2>
        <div>${langItems}</div>
      </div>
    `;
  }

  // Portfolio
  let portHtml = '';
  if (d.portfolio && d.portfolio.length > 0) {
    const portItems = d.portfolio.map(p => `
      <div class="cv-std-item">
        <div class="cv-std-item-header">
          <span>${p.title} ${p.role ? '(' + p.role + ')' : ''}</span>
        </div>
        ${p.url ? `<div><a href="${p.url}" target="_blank" style="color: #0284c7; text-decoration: underline;">${p.url}</a></div>` : ''}
        ${p.description ? `<div class="cv-std-desc">${p.description}</div>` : ''}
      </div>
    `).join('');
    portHtml = `
      <div class="cv-std-section">
        <h2 class="cv-std-heading">Portfolio &amp; Projects</h2>
        <div>${portItems}</div>
      </div>
    `;
  }

  // Referees
  let refHtml = '';
  if (d.referees && d.referees.length > 0) {
    const refItems = d.referees.map(r => `
      <div class="cv-std-item">
        <b>${r.name}</b> ${r.designation ? '– ' + r.designation : ''}${r.company ? ', ' + r.company : ''}
        ${r.contact ? ` <span class="cv-std-date">${r.contact}</span>` : ''}
      </div>
    `).join('');
    refHtml = `
      <div class="cv-std-section">
        <h2 class="cv-std-heading">Referees</h2>
        <div>${refItems}</div>
      </div>
    `;
  }

  return `
    <div>
      <div class="cv-std-header">
        <div>
          <h1 class="cv-std-name">${d.fullName || 'Your Full Name'}</h1>
          <div class="cv-std-contact-row">
            ${d.email ? `<span>${d.email}</span>` : ''}
            ${d.email && d.phone ? `<span>·</span>` : ''}
            ${d.phone ? `<span class="font-mono">Mobile: ${d.phone}</span>` : ''}
            ${d.address ? `<span>·</span><span>${d.address}</span>` : ''}
          </div>
        </div>
        ${photoHtml}
      </div>

      ${demographicsHtml}

      ${d.summary ? `
        <div class="cv-std-section">
          <h2 class="cv-std-heading">Summary</h2>
          <p class="cv-std-desc" style="border:none; padding-left:0;">${d.summary}</p>
        </div>
      ` : ''}

      ${d.skills && d.skills.length > 0 ? `
        <div class="cv-std-section">
          <h2 class="cv-std-heading">Key Skills</h2>
          <div class="cv-std-badge-list">
            ${d.skills.map(s => `<span class="cv-std-badge">${s}</span>`).join('')}
          </div>
        </div>
      ` : ''}

      ${expHtml}
      ${eduHtml}
      ${certHtml}
      ${langHtml}
      ${portHtml}
      ${refHtml}
    </div>
  `;
}

// 2. EXECUTIVE MODERN TEMPLATE (Pro Tier - Two Columns)
function renderExecutiveTemplate(d) {
  const photoHtml = d.photoUrl ? `
    <div class="cv-exec-photo">
      <img src="${d.photoUrl}" alt="${d.fullName}">
    </div>
  ` : '';

  const skillsHtml = d.skills && d.skills.length > 0 ? `
    <div class="cv-exec-side-section">
      <h3 class="cv-exec-side-heading">Competencies</h3>
      <div>
        ${d.skills.map(s => `<span class="cv-exec-skill-badge">${s}</span>`).join('')}
      </div>
    </div>
  ` : '';

  const langHtml = d.languages && d.languages.length > 0 ? `
    <div class="cv-exec-side-section">
      <h3 class="cv-exec-side-heading">Languages</h3>
      <div>
        ${d.languages.map(l => `<div class="cv-exec-side-item"><b>${l.language}</b><div style="font-size:10px; color:#64748b;">${l.proficiency}</div></div>`).join('')}
      </div>
    </div>
  ` : '';

  const refHtml = d.referees && d.referees.length > 0 ? `
    <div class="cv-exec-side-section">
      <h3 class="cv-exec-side-heading">References</h3>
      <div>
        ${d.referees.map(r => `
          <div class="cv-exec-side-item">
            <b>${r.name}</b>
            <div>${r.designation}${r.company ? ', ' + r.company : ''}</div>
            <div style="font-family: monospace; font-size: 10px; color: #047857;">${r.contact}</div>
          </div>
        `).join('')}
      </div>
    </div>
  ` : '';

  const expItems = (d.experience || []).map(e => `
    <div class="cv-exec-timeline-item">
      <div class="cv-exec-timeline-dot"></div>
      <div class="cv-exec-timeline-header">
        <span class="cv-exec-role">${e.role}</span>
        <span class="cv-exec-date-badge">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
      </div>
      <div class="cv-exec-company">${e.company}</div>
      ${e.description ? `<div style="font-size:12px; color:#334155; margin-top:4px; line-height:1.5;">${e.description}</div>` : ''}
    </div>
  `).join('');

  const eduItems = (d.education || []).map(e => {
    const instName = (e.institution === "Other / Overseas University" && e.customInstitution) ? e.customInstitution : e.institution;
    return `
      <div style="margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between; align-items:baseline; font-weight:700;">
          <span style="color:#0f172a;">${e.degree || e.level}</span>
          <span class="cv-exec-date-badge">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
        </div>
        <div style="color:#475569; font-size:12px;">${instName} ${e.grade ? '· ' + e.grade : ''}</div>
      </div>
    `;
  }).join('');

  return `
    <div class="cv-exec-layout">
      <!-- Left Column Sidebar -->
      <div class="cv-exec-sidebar">
        ${photoHtml}

        <div class="cv-exec-side-section">
          <h3 class="cv-exec-side-heading">Contact</h3>
          <div class="cv-exec-side-item"><b>Phone:</b> <span class="font-mono">${d.phone || '—'}</span></div>
          <div class="cv-exec-side-item"><b>Email:</b> <span style="word-break:break-all;">${d.email || '—'}</span></div>
          <div class="cv-exec-side-item"><b>Address:</b> <span>${d.address || '—'}</span></div>
        </div>

        <div class="cv-exec-side-section">
          <h3 class="cv-exec-side-heading">Demographics</h3>
          <div class="cv-exec-side-item"><b>National ID:</b> <span class="font-mono" style="font-weight:700;">${d.nationalId || '—'}</span></div>
          <div class="cv-exec-side-item"><b>DOB:</b> <span>${d.dob || '—'}</span></div>
          <div class="cv-exec-side-item"><b>Sex:</b> <span>${d.sex || 'Male'}</span></div>
          <div class="cv-exec-side-item"><b>Nationality:</b> <span>${d.nationality || 'Maldivian'}</span></div>
        </div>

        ${skillsHtml}
        ${langHtml}
        ${refHtml}
      </div>

      <!-- Right Column Main Content -->
      <div class="cv-exec-main">
        <div class="cv-exec-main-header">
          <h1 class="cv-exec-name">${d.fullName || 'Candidate Name'}</h1>
          <div class="cv-exec-title">${(d.experience && d.experience[0] && d.experience[0].role) ? d.experience[0].role : 'Executive Professional'}</div>
        </div>

        ${d.summary ? `
          <div class="cv-exec-summary">${d.summary}</div>
        ` : ''}

        ${expItems ? `
          <div>
            <h2 class="cv-exec-heading">Professional Experience</h2>
            <div class="cv-exec-timeline">${expItems}</div>
          </div>
        ` : ''}

        ${eduItems ? `
          <div style="margin-top:1.25rem;">
            <h2 class="cv-exec-heading">Education &amp; Qualifications</h2>
            <div>${eduItems}</div>
          </div>
        ` : ''}

        ${((d.certifications && d.certifications.length > 0) || d.training) ? `
          <div style="margin-top:1.25rem;">
            <h2 class="cv-exec-heading">Licensures &amp; Training</h2>
            <div style="font-size:12px; color:#334155; line-height:1.6;">
              ${(d.certifications || []).map(c => `<div>• <b>${c.title}</b> ${c.issuer ? '(' + c.issuer + ')' : ''} ${c.year ? '· ' + c.year : ''}</div>`).join('')}
              ${d.training ? `<div>${d.training}</div>` : ''}
            </div>
          </div>
        ` : ''}

        ${(d.portfolio && d.portfolio.length > 0) ? `
          <div style="margin-top:1.25rem;">
            <h2 class="cv-exec-heading">Projects &amp; Portfolio</h2>
            <div>
              ${d.portfolio.map(p => `
                <div style="margin-bottom:8px; font-size:12px;">
                  <b>${p.title}</b> ${p.role ? '(' + p.role + ')' : ''}
                  ${p.url ? `<div><a href="${p.url}" target="_blank" style="color:#047857; text-decoration:underline;">${p.url}</a></div>` : ''}
                  ${p.description ? `<p style="color:#475569; margin:2px 0 0 0;">${p.description}</p>` : ''}
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    </div>
  `;
}

// 3. CREATIVE MODERN TEMPLATE (Pro Tier - Timeline Badges & Accent Line)
