function renderModernTemplate(d) {
  const photoHtml = d.photoUrl ? `
    <div class="cv-mod-photo">
      <img src="${d.photoUrl}" alt="${d.fullName}">
    </div>
  ` : '';

  return `
    <div>
      <!-- Modern Accent Top Bar -->
      <div class="cv-mod-header">
        <div>
          <h1 class="cv-mod-name">${d.fullName || 'Candidate Full Name'}</h1>
          <div class="cv-mod-contact-row">
            ${d.email ? `<span>${d.email}</span>` : ''}
            ${d.email && d.phone ? `<span>·</span>` : ''}
            ${d.phone ? `<span class="font-mono">${d.phone}</span>` : ''}
            ${d.address ? `<span>·</span><span>${d.address}</span>` : ''}
          </div>
          <div class="cv-mod-demographics">
            NID: ${d.nationalId || '—'} · DOB: ${d.dob || '—'} · Sex: ${d.sex || 'Male'} · ${d.nationality || 'Maldivian'}
          </div>
        </div>
        ${photoHtml}
      </div>

      ${d.summary ? `
        <div class="cv-mod-section">
          <h2 class="cv-mod-heading">About Me</h2>
          <p style="font-size:12.5px; color:#334155; line-height:1.6; margin:0; white-space:pre-line;">${d.summary}</p>
        </div>
      ` : ''}

      ${d.skills && d.skills.length > 0 ? `
        <div class="cv-mod-section">
          <h2 class="cv-mod-heading">Areas of Expertise</h2>
          <div class="cv-mod-chips">
            ${d.skills.map(s => `<span class="cv-mod-chip">${s}</span>`).join('')}
          </div>
        </div>
      ` : ''}

      ${d.experience && d.experience.length > 0 ? `
        <div class="cv-mod-section">
          <h2 class="cv-mod-heading">Experience Timeline</h2>
          <div>
            ${d.experience.map(e => `
              <div class="cv-mod-card">
                <div class="cv-mod-card-header">
                  <span class="cv-mod-card-title">${e.role} · <span class="cv-mod-card-subtitle">${e.company}</span></span>
                  <span class="cv-mod-badge">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
                </div>
                ${e.description ? `<div style="font-size:12px; color:#475569; line-height:1.5; margin-top:4px; white-space:pre-line;">${e.description}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${d.education && d.education.length > 0 ? `
        <div class="cv-mod-section">
          <h2 class="cv-mod-heading">Education &amp; Academics</h2>
          <div class="cv-mod-grid-2">
            ${d.education.map(e => {
              const instName = (e.institution === "Other / Overseas University" && e.customInstitution) ? e.customInstitution : e.institution;
              return `
                <div class="cv-mod-card" style="margin-bottom:0;">
                  <div style="font-weight:700; color:#0f172a; font-size:12.5px;">${e.degree || e.level}</div>
                  <div style="color:#64748b; font-size:11.5px;">${instName}</div>
                  <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#64748b; font-family:monospace; margin-top:4px;">
                    <span>${e.grade || ''}</span>
                    <span>${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      ` : ''}

      ${(d.portfolio && d.portfolio.length > 0) ? `
        <div class="cv-mod-section">
          <h2 class="cv-mod-heading">Featured Projects</h2>
          <div class="cv-mod-grid-2">
            ${d.portfolio.map(p => `
              <div class="cv-mod-card" style="margin-bottom:0; background:#fffbeb; border-color:#fde68a;">
                <div style="font-weight:700; color:#0f172a; font-size:12px;">${p.title}</div>
                ${p.role ? `<div style="font-size:11px; color:#475569;">${p.role}</div>` : ''}
                ${p.url ? `<a href="${p.url}" target="_blank" style="color:#4338ca; text-decoration:underline; font-size:10.5px; display:block;">${p.url}</a>` : ''}
                ${p.description ? `<p style="font-size:11px; color:#334155; margin:2px 0 0 0;">${p.description}</p>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:1.25rem; padding-top:0.75rem; border-top:1px solid #e2e8f0; font-size:12px;">
        <div>
          <h3 style="font-weight:700; color:#312e81; margin:0 0 4px 0; font-size:11.5px; text-transform:uppercase;">Languages</h3>
          <div style="color:#334155; line-height:1.5;">
            ${(d.languages || []).map(l => `<div>• <b>${l.language}:</b> ${l.proficiency}</div>`).join('')}
          </div>
        </div>
        <div>
          <h3 style="font-weight:700; color:#312e81; margin:0 0 4px 0; font-size:11.5px; text-transform:uppercase;">References</h3>
          <div style="color:#334155; line-height:1.5;">
            ${(d.referees || []).map(r => `<div><b>${r.name}</b> (${r.designation}, ${r.company}) · <span style="font-family:monospace;">${r.contact}</span></div>`).join('')}
          </div>
        </div>
      </div>
    </div>
  `;
}

// 4. TECHNICAL / COMPACT ATS TEMPLATE (Pro Tier - Recruiter Optimized)
function renderTechnicalTemplate(d) {
  const expItems = (d.experience || []).map(e => `
    <div class="cv-tech-item">
      <div class="cv-tech-item-row">
        <span>${e.role.toUpperCase()} — ${e.company}</span>
        <span>${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
      </div>
      ${e.description ? `<div class="cv-tech-desc">${e.description}</div>` : ''}
    </div>
  `).join('');

  const eduItems = (d.education || []).map(e => {
    const instName = (e.institution === "Other / Overseas University" && e.customInstitution) ? e.customInstitution : e.institution;
    return `
      <div class="cv-tech-item-row" style="margin-bottom:4px;">
        <span><b>${e.degree || e.level}</b> — ${instName} ${e.grade ? '(' + e.grade + ')' : ''}</span>
        <span>${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
      </div>
    `;
  }).join('');

  return `
    <div>
      <!-- High Density ATS Header -->
      <div class="cv-tech-header">
        <h1 class="cv-tech-name">${d.fullName || 'Candidate Name'}</h1>
        <div class="cv-tech-meta">
          ${d.address || 'Maldives'} | Tel: ${d.phone || '—'} | Email: ${d.email || '—'}
        </div>
        <div class="cv-tech-meta" style="font-size:10px; color:#475569;">
          National ID: ${d.nationalId || '—'} | DOB: ${d.dob || '—'} | Gender: ${d.sex || 'Male'} | Nationality: ${d.nationality || 'Maldivian'}
        </div>
      </div>

      ${d.summary ? `
        <div class="cv-tech-section">
          <div class="cv-tech-heading">Professional Summary</div>
          <p style="margin:2px 0 0 0; line-height:1.5; color:#1e293b;">${d.summary}</p>
        </div>
      ` : ''}

      ${d.skills && d.skills.length > 0 ? `
        <div class="cv-tech-section">
          <div class="cv-tech-heading">Technical Skills &amp; Core Competencies</div>
          <div style="color:#1e293b;">${d.skills.join("  |  ")}</div>
        </div>
      ` : ''}

      ${expItems ? `
        <div class="cv-tech-section">
          <div class="cv-tech-heading">Professional Experience</div>
          <div>${expItems}</div>
        </div>
      ` : ''}

      ${eduItems ? `
        <div class="cv-tech-section">
          <div class="cv-tech-heading">Education &amp; Qualifications</div>
          <div>${eduItems}</div>
        </div>
      ` : ''}

      ${((d.certifications && d.certifications.length > 0) || d.training) ? `
        <div class="cv-tech-section">
          <div class="cv-tech-heading">Certifications &amp; Training</div>
          <div style="line-height:1.5; color:#1e293b;">
            ${(d.certifications || []).map(c => `<div>[CERT] ${c.title} — ${c.issuer || 'Authority'} (${c.year || 'N/A'})</div>`).join('')}
            ${d.training ? `<div>[ADDITIONAL] ${d.training}</div>` : ''}
          </div>
        </div>
      ` : ''}

      ${(d.portfolio && d.portfolio.length > 0) ? `
        <div class="cv-tech-section">
          <div class="cv-tech-heading">Projects &amp; Systems</div>
          <div style="line-height:1.5; color:#1e293b;">
            ${d.portfolio.map(p => `
              <div>
                <b>${p.title}</b> (${p.role || 'Contributor'}) ${p.url ? `— [${p.url}]` : ''}
                ${p.description ? `<div style="color:#475569;">${p.description}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:1rem; padding-top:0.5rem; border-top:1px solid #cbd5e1;">
        <div>
          <div class="cv-tech-heading" style="border:none; margin:0 0 2px 0;">Languages</div>
          <div>${(d.languages || []).map(l => `${l.language} (${l.proficiency})`).join(", ") || 'Dhivehi, English'}</div>
        </div>
        <div>
          <div class="cv-tech-heading" style="border:none; margin:0 0 2px 0;">References</div>
          <div>${(d.referees || []).map(r => `${r.name} - ${r.contact || 'Available'}`).join(" | ") || 'Available upon request'}</div>
        </div>
      </div>
    </div>
  `;
}

// Template Switching Logic
function selectTemplate(tmplKey, force = false) {
  // If user is selecting a paid template and is NOT paid
  if (tmplKey !== 'standard' && !userIsPaid && !force) {
    openProModal();
    return;
  }

  currentTemplate = tmplKey;

  // Update button active state with Vanilla CSS
  ['standard', 'executive', 'modern', 'technical'].forEach(k => {
    const btn = document.getElementById(`btn-tmpl-${k}`);
    if (btn) {
      if (k === tmplKey) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    }
  });

  const badgeNames = {
    standard: "Standard Maldivian",
    executive: "Executive Modern (PRO)",
    modern: "Creative Modern (PRO)",
    technical: "Technical ATS (PRO)"
  };
  document.getElementById("previewTemplateBadge").textContent = badgeNames[tmplKey] || "Standard Maldivian";

  renderLivePreview();
}

// Save CV to SQLite server (Pro feature)
async function saveCvToServer() {
  if (!currentUser) {
    if (typeof openGlobalAlertsModal === 'function') {
      openGlobalAlertsModal('auth');
    } else if (typeof openAuthModal === 'function') {
      openAuthModal('register');
    }
    return;
  }

  if (!userIsPaid) {
    openProModal();
    return;
  }

  const cvData = collectCvData();
  const statusEl = document.getElementById("saveStatus");
  const statusBar = document.getElementById("saveStatusBar");
  if (statusEl) statusEl.textContent = "Saving...";
  if (statusBar) statusBar.textContent = "Saving...";

  try {
    const res = await fetch("/api/cv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: `${cvData.fullName || 'Maldivian'} CV`,
        template: currentTemplate,
        data: cvData,
        photo_data: cvData.photoUrl
      })
    });
    if (res.ok) {
      statusEl.textContent = "Saved to account";
      setTimeout(() => { statusEl.textContent = "Ready"; }, 3000);
    } else if (res.status === 403) {
      openProModal();
      statusEl.textContent = "Pro Required";
    } else {
      statusEl.textContent = "Error saving";
    }
  } catch(e) {
    statusEl.textContent = "Connection error";
  }
}

// Clean Print with sanitized Document Title (so PDF save defaults to Candidate_Name_A4.pdf)
