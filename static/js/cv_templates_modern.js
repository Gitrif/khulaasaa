function renderModernTemplate(d) {
  const photoHtml = d.photoUrl ? `
    <div class="shrink-0 w-24 h-24 rounded-full overflow-hidden border-2 border-indigo-600 shadow-sm">
      <img src="${d.photoUrl}" alt="${d.fullName}" class="w-full h-full object-cover">
    </div>
  ` : '';

  return `
    <div class="space-y-6 font-sans">
      <!-- Modern Accent Top Bar -->
      <div class="border-b-4 border-indigo-700 pb-4 flex justify-between items-center gap-4">
        <div>
          <h1 class="text-3xl font-extrabold tracking-tight text-slate-950">${d.fullName || 'Candidate Full Name'}</h1>
          <div class="text-xs font-semibold text-indigo-700 mt-1 flex flex-wrap items-center gap-3">
            <span>${d.email || ''}</span>
            <span>·</span>
            <span class="font-mono">${d.phone || ''}</span>
            <span>·</span>
            <span>${d.address || 'Maldives'}</span>
          </div>
          <div class="text-[11px] text-slate-500 font-mono mt-1">
            NID: ${d.nationalId || '—'} · DOB: ${d.dob || '—'} · Sex: ${d.sex || 'Male'} · ${d.nationality || 'Maldivian'}
          </div>
        </div>
        ${photoHtml}
      </div>

      ${d.summary ? `
        <div class="space-y-1.5">
          <h2 class="text-xs font-bold uppercase tracking-wider text-indigo-900">About Me</h2>
          <p class="text-xs text-slate-700 leading-relaxed whitespace-pre-line">${d.summary}</p>
        </div>
      ` : ''}

      ${d.skills && d.skills.length > 0 ? `
        <div class="space-y-2">
          <h2 class="text-xs font-bold uppercase tracking-wider text-indigo-900">Areas of Expertise</h2>
          <div class="flex flex-wrap gap-1.5">
            ${d.skills.map(s => `<span class="px-2.5 py-1 bg-indigo-50 border border-indigo-200 text-indigo-900 text-xs font-semibold rounded">${s}</span>`).join('')}
          </div>
        </div>
      ` : ''}

      ${d.experience && d.experience.length > 0 ? `
        <div class="space-y-3">
          <h2 class="text-xs font-bold uppercase tracking-wider text-indigo-900">Experience Timeline</h2>
          <div class="space-y-3">
            ${d.experience.map(e => `
              <div class="p-3 rounded border border-slate-200 bg-slate-50/50 space-y-1">
                <div class="flex justify-between items-baseline">
                  <span class="font-bold text-slate-900 text-xs">${e.role} · <span class="font-normal text-indigo-800">${e.company}</span></span>
                  <span class="px-2 py-0.5 rounded bg-indigo-100 text-indigo-800 text-[10px] font-bold font-mono">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
                </div>
                ${e.description ? `<div class="text-xs text-slate-700 leading-relaxed whitespace-pre-line mt-1">${e.description}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${d.education && d.education.length > 0 ? `
        <div class="space-y-2">
          <h2 class="text-xs font-bold uppercase tracking-wider text-indigo-900">Education &amp; Academics</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            ${d.education.map(e => {
              const instName = (e.institution === "Other / Overseas University" && e.customInstitution) ? e.customInstitution : e.institution;
              return `
                <div class="p-2.5 border border-slate-200 rounded">
                  <div class="font-bold text-slate-900">${e.degree || e.level}</div>
                  <div class="text-slate-600 text-[11px]">${instName}</div>
                  <div class="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
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
        <div class="space-y-2">
          <h2 class="text-xs font-bold uppercase tracking-wider text-indigo-900">Featured Projects</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            ${d.portfolio.map(p => `
              <div class="p-2.5 bg-amber-50/60 border border-amber-200 rounded space-y-1">
                <div class="font-bold text-slate-900">${p.title}</div>
                ${p.role ? `<div class="text-[11px] text-slate-600 font-medium">${p.role}</div>` : ''}
                ${p.url ? `<a href="${p.url}" target="_blank" class="text-indigo-700 underline text-[10px] block">${p.url}</a>` : ''}
                ${p.description ? `<p class="text-[11px] text-slate-700 leading-tight">${p.description}</p>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <div class="grid grid-cols-2 gap-4 pt-2 border-t border-slate-200 text-xs">
        <div>
          <h3 class="font-bold text-indigo-900 mb-1">Languages</h3>
          <div class="space-y-0.5 text-slate-700">
            ${(d.languages || []).map(l => `<div>• <b>${l.language}:</b> ${l.proficiency}</div>`).join('')}
          </div>
        </div>
        <div>
          <h3 class="font-bold text-indigo-900 mb-1">References</h3>
          <div class="space-y-1 text-slate-700">
            ${(d.referees || []).map(r => `<div><b>${r.name}</b> (${r.designation}, ${r.company}) · <span class="font-mono">${r.contact}</span></div>`).join('')}
          </div>
        </div>
      </div>
    </div>
  `;
}

// 4. TECHNICAL / COMPACT ATS TEMPLATE (Pro Tier - Recruiter Optimized)
function renderTechnicalTemplate(d) {
  return `
    <div class="space-y-4 font-mono text-slate-900 text-xs leading-normal">
      <!-- High Density ATS Header -->
      <div class="text-center border-b border-slate-900 pb-3">
        <h1 class="text-xl font-bold tracking-tight text-slate-950 font-sans uppercase">${d.fullName || 'Candidate Name'}</h1>
        <div class="text-[11px] text-slate-700 mt-1">
          ${d.address || 'Maldives'} | Tel: ${d.phone || '—'} | Email: ${d.email || '—'}
        </div>
        <div class="text-[10px] text-slate-500 mt-0.5">
          National ID: ${d.nationalId || '—'} | DOB: ${d.dob || '—'} | Gender: ${d.sex || 'Male'} | Nationality: ${d.nationality || 'Maldivian'}
        </div>
      </div>

      ${d.summary ? `
        <div class="space-y-1">
          <div class="font-bold uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-0.5 font-sans">Professional Summary</div>
          <p class="text-slate-800 text-[11px] leading-relaxed">${d.summary}</p>
        </div>
      ` : ''}

      ${d.skills && d.skills.length > 0 ? `
        <div class="space-y-1">
          <div class="font-bold uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-0.5 font-sans">Technical Skills &amp; Core Competencies</div>
          <div class="text-[11px] text-slate-800">${d.skills.join("  |  ")}</div>
        </div>
      ` : ''}

      ${d.experience && d.experience.length > 0 ? `
        <div class="space-y-2">
          <div class="font-bold uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-0.5 font-sans">Professional Experience</div>
          <div class="space-y-2.5">
            ${d.experience.map(e => `
              <div>
                <div class="flex justify-between font-bold text-slate-900">
                  <span>${e.role.toUpperCase()} — ${e.company}</span>
                  <span>${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
                </div>
                ${e.description ? `<div class="text-[11px] text-slate-700 whitespace-pre-line pl-2 mt-0.5 border-l border-slate-400">${e.description}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${d.education && d.education.length > 0 ? `
        <div class="space-y-1">
          <div class="font-bold uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-0.5 font-sans">Education &amp; Qualifications</div>
          <div class="space-y-1.5">
            ${d.education.map(e => {
              const instName = (e.institution === "Other / Overseas University" && e.customInstitution) ? e.customInstitution : e.institution;
              return `
                <div class="flex justify-between text-[11px]">
                  <span><b>${e.degree || e.level}</b> — ${instName} ${e.grade ? `(${e.grade})` : ''}</span>
                  <span>${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      ` : ''}

      ${((d.certifications && d.certifications.length > 0) || d.training) ? `
        <div class="space-y-1">
          <div class="font-bold uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-0.5 font-sans">Certifications &amp; Training</div>
          <div class="text-[11px] space-y-0.5 text-slate-800">
            ${(d.certifications || []).map(c => `<div>[CERT] ${c.title} — ${c.issuer || 'Authority'} (${c.year || 'N/A'})</div>`).join('')}
            ${d.training ? `<div class="whitespace-pre-line">[ADDITIONAL] ${d.training}</div>` : ''}
          </div>
        </div>
      ` : ''}

      ${(d.portfolio && d.portfolio.length > 0) ? `
        <div class="space-y-1">
          <div class="font-bold uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-0.5 font-sans">Projects &amp; Systems</div>
          <div class="space-y-1 text-[11px]">
            ${d.portfolio.map(p => `
              <div>
                <b>${p.title}</b> (${p.role || 'Contributor'}) ${p.url ? `— [${p.url}]` : ''}
                ${p.description ? `<div class="text-slate-700">${p.description}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <div class="grid grid-cols-2 gap-4 pt-2 border-t border-slate-300 text-[11px]">
        <div>
          <div class="font-bold uppercase font-sans">Languages</div>
          <div>${(d.languages || []).map(l => `${l.language} (${l.proficiency})`).join(", ") || 'Dhivehi, English'}</div>
        </div>
        <div>
          <div class="font-bold uppercase font-sans">References</div>
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

  // Update button borders
  ['standard', 'executive', 'modern', 'technical'].forEach(k => {
    const btn = document.getElementById(`btn-tmpl-${k}`);
    if (btn) {
      if (k === tmplKey) {
        btn.classList.add("border-lagoon", "bg-emerald-50/50");
      } else {
        btn.classList.remove("border-lagoon", "bg-emerald-50/50");
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
    openAuthModal('register');
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
