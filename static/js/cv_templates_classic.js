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

  if (currentTemplate === 'executive') {
    paper.innerHTML = renderExecutiveTemplate(d);
  } else if (currentTemplate === 'modern') {
    paper.innerHTML = renderModernTemplate(d);
  } else if (currentTemplate === 'technical') {
    paper.innerHTML = renderTechnicalTemplate(d);
  } else {
    paper.innerHTML = renderStandardTemplate(d);
  }
}

// 1. STANDARD MALDIVIAN TEMPLATE (Free Default)
function renderStandardTemplate(d) {
  // Photo rendering rule: IF NO PHOTO, DO NOT PRINT PLACEHOLDER BOX
  const photoHtml = d.photoUrl ? `
    <div class="shrink-0 w-24 h-28 border border-slate-300 rounded overflow-hidden bg-slate-50 flex items-center justify-center shadow-xs">
      <img src="${d.photoUrl}" alt="${d.fullName}" class="w-full h-full object-cover">
    </div>
  ` : '';

  // Demographics Bar
  const demographicsHtml = `
    <div class="text-xs text-slate-800 py-1.5 border-t border-b border-slate-300 font-medium my-4 flex flex-wrap gap-x-3 gap-y-1">
      <span><b>Sex:</b> ${d.sex || 'Male'}</span>
      <span class="text-slate-300">|</span>
      <span><b>DOB:</b> ${d.dob || '—'}</span>
      <span class="text-slate-300">|</span>
      <span><b>Nationality:</b> ${d.nationality || 'Maldivian'}</span>
      <span class="text-slate-300">|</span>
      <span><b>National ID#:</b> <span class="font-mono font-bold">${d.nationalId || '—'}</span></span>
    </div>
  `;

  // Experience List
  let expHtml = '';
  if (d.experience && d.experience.length > 0) {
    const items = d.experience.map(e => `
      <div class="space-y-1">
        <div class="flex flex-wrap justify-between items-baseline font-bold text-slate-900">
          <span>${e.role || 'Designation'} ${e.company ? '– ' + e.company : ''}</span>
          <span class="text-xs font-semibold text-slate-600 font-mono">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
        </div>
        ${e.description ? `<div class="text-slate-700 leading-relaxed whitespace-pre-line pl-2 border-l-2 border-slate-200 text-xs">${e.description}</div>` : ''}
      </div>
    `).join('');
    expHtml = `
      <div class="space-y-3">
        <h2 class="text-sm font-bold uppercase tracking-wide text-slate-900 border-b-2 border-slate-800 pb-1">Experience</h2>
        <div class="space-y-3 text-xs">${items}</div>
      </div>
    `;
  }

  // Education List
  let eduHtml = '';
  if (d.education && d.education.length > 0) {
    const items = d.education.map(e => {
      const instName = (e.institution === "Other / Overseas University" && e.customInstitution) ? e.customInstitution : e.institution;
      return `
        <div class="flex flex-wrap justify-between items-baseline text-xs">
          <div>
            <span class="font-bold text-slate-900">${e.degree || e.level}</span>
            ${instName ? ` <span class="text-slate-700">– ${instName}</span>` : ''}
            ${e.grade ? ` <span class="text-slate-500">(${e.grade})</span>` : ''}
          </div>
          <span class="text-xs font-semibold text-slate-600 font-mono">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
        </div>
      `;
    }).join('');
    eduHtml = `
      <div class="space-y-2">
        <h2 class="text-sm font-bold uppercase tracking-wide text-slate-900 border-b-2 border-slate-800 pb-1">Education</h2>
        <div class="space-y-2">${items}</div>
      </div>
    `;
  }

  // Certifications
  let certHtml = '';
  if ((d.certifications && d.certifications.length > 0) || d.training) {
    const certList = (d.certifications || []).map(c => `
      <div>• <b>${c.title}</b> ${c.issuer ? `– ${c.issuer}` : ''} ${c.year ? `(${c.year})` : ''}</div>
    `).join('');
    certHtml = `
      <div class="space-y-2">
        <h2 class="text-sm font-bold uppercase tracking-wide text-slate-900 border-b-2 border-slate-800 pb-1">Other Training &amp; Certifications</h2>
        <div class="text-xs text-slate-700 space-y-1">
          ${certList}
          ${d.training ? `<div class="whitespace-pre-line">${d.training}</div>` : ''}
        </div>
      </div>
    `;
  }

  // Languages
  let langHtml = '';
  if (d.languages && d.languages.length > 0) {
    const langItems = d.languages.map(l => `<div>• <b>${l.language}:</b> ${l.proficiency}</div>`).join('');
    langHtml = `
      <div class="space-y-2">
        <h2 class="text-sm font-bold uppercase tracking-wide text-slate-900 border-b-2 border-slate-800 pb-1">Languages</h2>
        <div class="text-xs text-slate-700 space-y-1">${langItems}</div>
      </div>
    `;
  }

  // Portfolio
  let portHtml = '';
  if (d.portfolio && d.portfolio.length > 0) {
    const portItems = d.portfolio.map(p => `
      <div class="text-xs">
        <div class="font-bold text-slate-900">${p.title} ${p.role ? `<span class="font-normal text-slate-600">(${p.role})</span>` : ''}</div>
        ${p.url ? `<a href="${p.url}" target="_blank" class="text-sky-700 underline text-[11px]">${p.url}</a>` : ''}
        ${p.description ? `<p class="text-slate-700 mt-0.5">${p.description}</p>` : ''}
      </div>
    `).join('');
    portHtml = `
      <div class="space-y-2">
        <h2 class="text-sm font-bold uppercase tracking-wide text-slate-900 border-b-2 border-slate-800 pb-1">Portfolio &amp; Projects</h2>
        <div class="space-y-2">${portItems}</div>
      </div>
    `;
  }

  // Referees
  let refHtml = '';
  if (d.referees && d.referees.length > 0) {
    const refItems = d.referees.map(r => `
      <div class="text-xs">
        <span class="font-bold text-slate-900">${r.name}</span>
        ${r.designation ? ` (${r.designation}` : ''}${r.company ? `, ${r.company})` : (r.designation ? ')' : '')}
        ${r.contact ? ` <span class="font-mono text-slate-700 ml-1">${r.contact}</span>` : ''}
      </div>
    `).join('');
    refHtml = `
      <div class="space-y-2">
        <h2 class="text-sm font-bold uppercase tracking-wide text-slate-900 border-b-2 border-slate-800 pb-1">Referees</h2>
        <div class="space-y-1">${refItems}</div>
      </div>
    `;
  }

  return `
    <div class="space-y-5 text-slate-900 font-sans">
      <div class="flex justify-between items-start gap-4">
        <div class="space-y-1">
          <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 leading-tight">${d.fullName || 'Your Full Name'}</h1>
          <div class="text-xs text-sky-700">${d.email || ''}</div>
          <div class="text-xs text-slate-600">${d.address || ''}</div>
          <div class="text-xs text-slate-600 font-mono">${d.phone ? `Mobile ${d.phone}` : ''}</div>
        </div>
        ${photoHtml}
      </div>

      ${demographicsHtml}

      ${d.summary ? `
        <div class="space-y-2">
          <h2 class="text-sm font-bold uppercase tracking-wide text-slate-900 border-b-2 border-slate-800 pb-1">Summary</h2>
          <p class="text-xs text-slate-700 leading-relaxed whitespace-pre-line">${d.summary}</p>
        </div>
      ` : ''}

      ${d.skills && d.skills.length > 0 ? `
        <div class="space-y-2">
          <h2 class="text-sm font-bold uppercase tracking-wide text-slate-900 border-b-2 border-slate-800 pb-1">Key Skills</h2>
          <ul class="text-xs text-slate-700 list-disc list-inside space-y-1">
            ${d.skills.map(s => `<li>${s}</li>`).join('')}
          </ul>
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
    <div class="w-28 h-32 mx-auto mb-4 border-2 border-emerald-700 rounded-sm overflow-hidden shadow-sm">
      <img src="${d.photoUrl}" alt="${d.fullName}" class="w-full h-full object-cover">
    </div>
  ` : '';

  const skillsHtml = d.skills && d.skills.length > 0 ? `
    <div class="space-y-1.5">
      <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-900 border-b border-emerald-700 pb-1">Core Competencies</h3>
      <div class="flex flex-wrap gap-1 pt-1">
        ${d.skills.map(s => `<span class="px-2 py-0.5 bg-emerald-50 text-emerald-950 font-medium rounded text-[11px] border border-emerald-200">${s}</span>`).join('')}
      </div>
    </div>
  ` : '';

  const langHtml = d.languages && d.languages.length > 0 ? `
    <div class="space-y-1.5">
      <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-900 border-b border-emerald-700 pb-1">Languages</h3>
      <div class="space-y-1 text-xs text-slate-800">
        ${d.languages.map(l => `<div><span class="font-semibold">${l.language}</span><div class="text-[10px] text-slate-600">${l.proficiency}</div></div>`).join('')}
      </div>
    </div>
  ` : '';

  const refHtml = d.referees && d.referees.length > 0 ? `
    <div class="space-y-1.5">
      <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-900 border-b border-emerald-700 pb-1">References</h3>
      <div class="space-y-2 text-xs text-slate-800">
        ${d.referees.map(r => `
          <div>
            <div class="font-bold">${r.name}</div>
            <div class="text-[11px] text-slate-600">${r.designation}${r.company ? `, ${r.company}` : ''}</div>
            <div class="text-[10px] font-mono text-emerald-800">${r.contact}</div>
          </div>
        `).join('')}
      </div>
    </div>
  ` : '';

  const expItems = (d.experience || []).map(e => `
    <div class="relative pl-4 border-l-2 border-emerald-600 space-y-1 pb-3">
      <div class="absolute -left-[5px] top-1 w-2 h-2 rounded-full bg-emerald-600"></div>
      <div class="flex justify-between items-baseline">
        <h4 class="font-bold text-slate-900 text-xs">${e.role}</h4>
        <span class="text-[11px] font-semibold text-emerald-800 font-mono">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
      </div>
      <div class="text-xs text-slate-600 font-medium">${e.company}</div>
      ${e.description ? `<div class="text-xs text-slate-700 leading-relaxed whitespace-pre-line mt-1">${e.description}</div>` : ''}
    </div>
  `).join('');

  const eduItems = (d.education || []).map(e => {
    const instName = (e.institution === "Other / Overseas University" && e.customInstitution) ? e.customInstitution : e.institution;
    return `
      <div class="text-xs space-y-0.5">
        <div class="flex justify-between items-baseline font-bold text-slate-900">
          <span>${e.degree || e.level}</span>
          <span class="text-[11px] font-mono font-semibold text-emerald-800">${formatDateRange(e.fromDate, e.toDate, e.isCurrent)}</span>
        </div>
        <div class="text-slate-600">${instName} ${e.grade ? `· <span class="text-slate-800 font-medium">${e.grade}</span>` : ''}</div>
      </div>
    `;
  }).join('');

  return `
    <div class="grid grid-cols-12 gap-6 font-sans">
      <!-- Left Column (4 cols) -->
      <div class="col-span-4 bg-slate-50/70 p-4 rounded-sm border border-slate-200 space-y-5">
        ${photoHtml}
        
        <div class="space-y-2 text-xs">
          <h3 class="font-bold uppercase tracking-wider text-emerald-900 border-b border-emerald-700 pb-1">Contact</h3>
          <div class="space-y-1 text-slate-700">
            <div><b>Phone:</b> <span class="font-mono">${d.phone || '—'}</span></div>
            <div><b>Email:</b> <span class="break-all">${d.email || '—'}</span></div>
            <div><b>Address:</b> ${d.address || '—'}</div>
          </div>
        </div>

        <div class="space-y-2 text-xs">
          <h3 class="font-bold uppercase tracking-wider text-emerald-900 border-b border-emerald-700 pb-1">Demographics</h3>
          <div class="space-y-1 text-slate-700">
            <div><b>National ID:</b> <span class="font-mono font-bold">${d.nationalId || '—'}</span></div>
            <div><b>DOB:</b> ${d.dob || '—'}</div>
            <div><b>Sex:</b> ${d.sex || 'Male'}</div>
            <div><b>Nationality:</b> ${d.nationality || 'Maldivian'}</div>
          </div>
        </div>

        ${skillsHtml}
        ${langHtml}
        ${refHtml}
      </div>

      <!-- Right Column (8 cols) -->
      <div class="col-span-8 space-y-5">
        <div>
          <h1 class="text-2xl font-bold tracking-tight text-emerald-950 uppercase">${d.fullName || 'Candidate Name'}</h1>
          <div class="text-xs font-semibold uppercase tracking-wider text-emerald-800 mt-0.5">
            ${(d.experience && d.experience[0] && d.experience[0].role) ? d.experience[0].role : 'Professional Executive'}
          </div>
        </div>

        ${d.summary ? `
          <div class="space-y-1.5">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-900 border-b-2 border-emerald-700 pb-1">Executive Summary</h2>
            <p class="text-xs text-slate-700 leading-relaxed whitespace-pre-line">${d.summary}</p>
          </div>
        ` : ''}

        ${expItems ? `
          <div class="space-y-3">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-900 border-b-2 border-emerald-700 pb-1">Professional Experience</h2>
            <div class="space-y-2">${expItems}</div>
          </div>
        ` : ''}

        ${eduItems ? `
          <div class="space-y-2.5">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-900 border-b-2 border-emerald-700 pb-1">Education &amp; Credentials</h2>
            <div class="space-y-2">${eduItems}</div>
          </div>
        ` : ''}

        ${((d.certifications && d.certifications.length > 0) || d.training) ? `
          <div class="space-y-2">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-900 border-b-2 border-emerald-700 pb-1">Licensures &amp; Training</h2>
            <div class="text-xs text-slate-700 space-y-1">
              ${(d.certifications || []).map(c => `<div>• <b>${c.title}</b> ${c.issuer ? `(${c.issuer})` : ''} ${c.year ? `· ${c.year}` : ''}</div>`).join('')}
              ${d.training ? `<div class="whitespace-pre-line">${d.training}</div>` : ''}
            </div>
          </div>
        ` : ''}

        ${(d.portfolio && d.portfolio.length > 0) ? `
          <div class="space-y-2">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-900 border-b-2 border-emerald-700 pb-1">Projects &amp; Portfolio</h2>
            <div class="space-y-2">
              ${d.portfolio.map(p => `
                <div class="text-xs">
                  <div class="font-bold text-slate-900">${p.title} ${p.role ? `<span class="font-normal text-slate-600">(${p.role})</span>` : ''}</div>
                  ${p.url ? `<a href="${p.url}" target="_blank" class="text-emerald-700 underline text-[11px]">${p.url}</a>` : ''}
                  ${p.description ? `<p class="text-slate-700 text-[11px] mt-0.5">${p.description}</p>` : ''}
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
