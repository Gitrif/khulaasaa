let currentLang = 'en';
let activePrintDocId = 'printableLetterContainer';
const _bwBoot = document.getElementById('bidWorkspaceBootstrap');
if (_bwBoot) {
  try { window.BID_CONTEXT = JSON.parse(_bwBoot.getAttribute('data-bid') || '{}'); } catch (e) {}
  try { window.SERVER_PROFILE = JSON.parse(_bwBoot.getAttribute('data-profile') || 'null'); } catch (e) {}
  window.SERVER_IS_PAID = _bwBoot.getAttribute('data-is-paid') === 'true';
}
const fmtMvr = val => (parseFloat(val) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const setTxt = (id, txt) => { const el = document.getElementById(id); if (el) el.innerText = txt; };

function switchSuiteTab(tabId) {
  document.querySelectorAll('.suite-content-pane').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.suite-tab-btn').forEach(el => {
    el.classList.remove('active-tab', 'border-lagoon', 'bg-white', 'shadow-2xs');
    el.classList.add('border-transparent');
    const icon = el.querySelector('svg');
    if (icon) { icon.classList.remove('text-lagoon'); icon.classList.add('text-slate-500'); }
  });

  const pane = document.getElementById('suiteTab-' + tabId);
  const btn = document.getElementById('tabBtn-' + tabId);
  if (pane) pane.style.display = 'block';
  if (btn) {
    btn.classList.add('active-tab', 'border-lagoon', 'bg-white', 'shadow-2xs');
    btn.classList.remove('border-transparent');
    const icon = btn.querySelector('svg');
    if (icon) { icon.classList.add('text-lagoon'); icon.classList.remove('text-slate-500'); }
  }

  const docMap = {
    'letters': 'printableLetterContainer',
    'proposal': 'printableProposalContainer',
    'quote': 'printableQuoteContainer',
    'boq': 'printableBoqContainer',
    'invoice': 'printableInvoiceContainer'
  };
  if (docMap[tabId]) activePrintDocId = docMap[tabId];
}

// TAB 1: LETTERS & CORRESPONDENCE
function setLetterLanguage(lang) {
  currentLang = lang;
  updateLetterContent();
}

function getLetterFormData() {
  const g = id => (document.getElementById(id)?.value || '').trim();
  const compName = g('letCompName') || 'Your Company Name';
  const compReg = g('letCompReg') || 'C0000000';
  const compTin = g('letCompTin') || '1000000';
  const signatory = g('letSignatory') || 'Authorized Signatory';
  const phone = g('letPhone') || '+960 777 0000';
  const email = g('letEmail') || 'info@company.mv';
  const agencyEmail = g('letAgencyEmail');
  const customQueries = g('letCustomQueries');

  try {
    localStorage.setItem('khulaasaa_bidder_company', JSON.stringify({
      name: compName, reg: compReg, tin: compTin, signatory, phone, email
    }));
  } catch (e) {}

  return { compName, compReg, compTin, signatory, phone, email, agencyEmail, customQueries };
}

function updateLetterContent() {
  const form = getLetterFormData();
  const letterTypeEl = document.querySelector('input[name="letterType"]:checked');
  const letterType = letterTypeEl ? letterTypeEl.value : 'registration';

  const inqBlock = document.getElementById('inquirySpecificBlock');
  if (inqBlock) inqBlock.style.display = (letterType === 'inquiry') ? 'block' : 'none';

  const dateStrEn = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });

  setTxt('prevLetterCompName', form.compName);
  setTxt('prevLetterCompReg', 'Reg No: ' + form.compReg);
  setTxt('prevLetterCompTin', 'MIRA TIN: ' + form.compTin);
  setTxt('prevLetterCompPhone', form.phone);
  setTxt('prevLetterCompEmail', form.email);
  setTxt('prevLetterCompSign', form.compName);

  let sigName = form.signatory, sigTitle = 'Authorized Signatory';
  if (form.signatory.includes('(')) {
    const parts = form.signatory.split('(');
    sigName = parts[0].trim();
    sigTitle = parts[1].replace(')', '').trim();
  }
  setTxt('prevLetterSignatoryName', sigName);
  setTxt('prevLetterSignatoryTitle', sigTitle);

  const letterContainer = document.getElementById('printableLetterContainer');
  if (!letterContainer) return;

  setTxt('prevLetterDate', 'Date: ' + dateStrEn);
  setTxt('prevLetterAgencyTitle', 'The Procurement Section / Tender Committee');
  setTxt('prevLetterAgencyName', window.BID_CONTEXT?.agency || 'Public Authority');
  setTxt('prevLetterAgencyLocation', window.BID_CONTEXT?.submissionLocation || 'Male, Maldives');
  setTxt('prevLetterSignoff', 'Yours sincerely,');

  const regInfo = `Registration No: <code>${form.compReg}</code>, TIN: <code>${form.compTin}</code>`;

  if (letterType === 'registration') {
    setTxt('prevLetterSubject', `Subject: Bidder Registration & Document Request — Ref: ${window.BID_CONTEXT?.referenceNumber || window.BID_CONTEXT?.noticeId}`);
    document.getElementById('prevLetterBody').innerHTML = `<p>Dear Sir / Madam,</p><p>We, <strong>${form.compName}</strong> (${regInfo}), hereby formally express our keen interest in participating in the public procurement tender for <strong>"${window.BID_CONTEXT?.titleEn}"</strong> (Reference: <code>${window.BID_CONTEXT?.referenceNumber || window.BID_CONTEXT?.noticeId}</code>).</p><p>In accordance with the gazette announcement, we kindly request your office to complete our registration as an official bidder and facilitate access to the full tender dossier, project specifications, and Bill of Quantities (BOQ).</p><p>Please transmit all relevant bidding documents and instructions to our corporate contact at <strong>${form.email}</strong> or telephone <strong>${form.phone}</strong>.</p><p>We confirm our commitment to comply with the public procurement procedures and regulations of the Government of Maldives.</p>`;
  } else if (letterType === 'inquiry') {
    setTxt('prevLetterSubject', `Subject: Pre-Bid Clarifications & Inquiries — Ref: ${window.BID_CONTEXT?.referenceNumber || window.BID_CONTEXT?.noticeId}`);
    const queryList = form.customQueries ? `<div class="p-3 bg-slate-50 border border-slate-200 rounded font-mono text-[11px] whitespace-pre-wrap">${form.customQueries}</div>` : `<p><em>[Please specify technical drawings or timeline questions using the inquiries field]</em></p>`;
    document.getElementById('prevLetterBody').innerHTML = `<p>Dear Sir / Madam,</p><p>With reference to the tender notice for <strong>"${window.BID_CONTEXT?.titleEn}"</strong> (Ref: <code>${window.BID_CONTEXT?.referenceNumber || window.BID_CONTEXT?.noticeId}</code>), we would like to request official clarifications regarding technical specifications:</p>${queryList}<p>We kindly request written responses before the pre-bid deadline so our team may formulate a compliant tender submission.</p>`;
  } else {
    setTxt('prevLetterSubject', `Subject: Formal Bid Submission — Ref: ${window.BID_CONTEXT?.referenceNumber || window.BID_CONTEXT?.noticeId}`);
    document.getElementById('prevLetterBody').innerHTML = `<p>Dear Sir / Madam,</p><p>We, the undersigned, having examined the bidding documents for <strong>"${window.BID_CONTEXT?.titleEn}"</strong> (Reference: <code>${window.BID_CONTEXT?.referenceNumber || window.BID_CONTEXT?.noticeId}</code>), hereby offer to execute the required works/services in strict conformity with the conditions of the contract.</p><p>We confirm that our bid proposal remains valid for the required validity period specified in the tender notice.</p><p>Accompanying this letter, we submit our technical proposal, corporate profile, financial schedule, and bid documentation.</p>`;
  }

  updateMailtoLink(form);
}

function updateMailtoLink(form) {
  const recipient = form.agencyEmail || window.BID_CONTEXT?.agencyEmail || '';
  const subj = document.getElementById('prevLetterSubject')?.innerText.replace('Subject: ', '') || 'Tender Inquiry';
  const bodyText = (document.getElementById('prevLetterBody')?.innerText || '').replace(/\n\s*\n/g, '\n\n');
  const fullBody = bodyText + `\n\nKind regards,\n${form.signatory}\n${form.compName}\nPhone: ${form.phone}\nEmail: ${form.email}`;
  const mailtoBtn = document.getElementById('btnSendEmailMailto');
  if (mailtoBtn) mailtoBtn.href = `mailto:${encodeURIComponent(recipient)}?subject=${encodeURIComponent(subj)}&body=${encodeURIComponent(fullBody)}`;
}

function copyLetterTextToClipboard() {
  const subj = document.getElementById('prevLetterSubject')?.innerText || '';
  const body = document.getElementById('prevLetterBody')?.innerText || '';
  const sig = document.getElementById('prevLetterSignatoryName')?.innerText || '';
  const tit = document.getElementById('prevLetterSignatoryTitle')?.innerText || '';
  const comp = document.getElementById('prevLetterCompSign')?.innerText || '';
  navigator.clipboard.writeText(`${subj}\n\n${body}\n\nYours sincerely,\n${sig}\n${tit}\n${comp}`).then(() => {
    const l = document.getElementById('copyBtnLabel');
    if (l) { l.innerText = 'Copied to Clipboard!'; setTimeout(() => { l.innerText = 'Copy Text'; }, 2500); }
  });
}

// TAB 3: TECHNICAL PROPOSAL & METHOD STATEMENT
function updateProposalPreview() {
  const form = getLetterFormData();
  const g = id => (document.getElementById(id)?.value || '').trim();
  setTxt('prevPropCompName', form.compName);
  setTxt('prevPropCompReg', 'Reg: ' + form.compReg);
  setTxt('prevPropExecSummary', g('propExecSummary'));
  setTxt('prevPropMethodology', g('propMethodology'));
  setTxt('prevPropSafetyQa', g('propSafetyQa'));
  setTxt('prevPropTeamLead', g('propTeamLead') || 'Mohamed Waheed (Project Lead)');
  setTxt('prevPropEngineer', g('propEngineer') || 'Ibrahim Rasheed (Site Engineer)');
  setTxt('prevPropSignatory', form.signatory);
  setTxt('prevPropSignComp', form.compName);
}

// TAB 4: COMMERCIAL PRICE QUOTATION
let quoteItems = [
  { desc: 'Main contract deliverables and supply package as per specifications', qty: 1, unit: 'Lot', rate: 45000.00 },
  { desc: 'Logistics, island freight, offloading, and site handling', qty: 1, unit: 'Lot', rate: 7500.00 },
  { desc: 'Testing, commissioning, warranty, and handover documentation', qty: 1, unit: 'Lot', rate: 5000.00 }
];

function renderQuoteItemsTable() {
  const tbody = document.getElementById('quoteInputItemsTable');
  const prevTbody = document.getElementById('prevQuoteTableBody');
  if (!tbody || !prevTbody) return;
  tbody.innerHTML = ''; prevTbody.innerHTML = '';
  let subtotal = 0;
  const currency = document.getElementById('quoteCurrency')?.value || 'MVR';

  quoteItems.forEach((item, idx) => {
    const amount = (item.qty || 0) * (item.rate || 0);
    subtotal += amount;

    const tr = document.createElement('tr');
    tr.className = 'border-b border-hairline/60';
    tr.innerHTML = `<td class="py-1.5 pr-2"><input type="text" value="${item.desc}" oninput="quoteItems[${idx}].desc=this.value; updateQuotePreview();" class="w-full text-xs p-1 border border-hairline rounded"></td><td class="py-1.5 px-1 w-16"><input type="number" value="${item.qty}" min="1" oninput="quoteItems[${idx}].qty=parseFloat(this.value)||0; renderQuoteItemsTable(); updateQuotePreview();" class="w-full text-xs p-1 border border-hairline rounded text-center"></td><td class="py-1.5 px-1 w-16"><input type="text" value="${item.unit}" oninput="quoteItems[${idx}].unit=this.value; updateQuotePreview();" class="w-full text-xs p-1 border border-hairline rounded text-center"></td><td class="py-1.5 px-1 w-24"><input type="number" value="${item.rate}" min="0" step="50" oninput="quoteItems[${idx}].rate=parseFloat(this.value)||0; renderQuoteItemsTable(); updateQuotePreview();" class="w-full text-xs p-1 border border-hairline rounded text-right"></td><td class="py-1.5 pl-1 w-8 text-center"><button type="button" onclick="removeQuoteItem(${idx})" class="text-rose-600 font-bold hover:text-rose-800">&times;</button></td>`;
    tbody.appendChild(tr);

    const prevTr = document.createElement('tr');
    prevTr.className = 'border-b border-hairline/60 text-xs';
    prevTr.innerHTML = `<td class="py-2 pr-2 text-slate-500 font-mono">${idx + 1}</td><td class="py-2 pr-2 font-medium text-ink">${item.desc}</td><td class="py-2 px-2 text-center text-slate">${item.qty}</td><td class="py-2 px-2 text-center text-slate">${item.unit}</td><td class="py-2 px-2 text-right font-mono">${fmtMvr(item.rate)}</td><td class="py-2 pl-2 text-right font-mono font-semibold text-ink">${fmtMvr(amount)}</td>`;
    prevTbody.appendChild(prevTr);
  });

  const gstChecked = document.getElementById('quoteGstCheck')?.checked !== false;
  const gstAmount = subtotal * (gstChecked ? 0.08 : 0);
  const total = subtotal + gstAmount;

  setTxt('prevQuoteCurrencyLabel', currency);
  setTxt('prevQuoteSubtotal', currency + ' ' + fmtMvr(subtotal));
  setTxt('prevQuoteGstLabel', gstChecked ? 'MIRA GST (8%):' : 'MIRA GST (0%):');
  setTxt('prevQuoteGst', currency + ' ' + fmtMvr(gstAmount));
  setTxt('prevQuoteTotal', currency + ' ' + fmtMvr(total));

  const invTotalInput = document.getElementById('invContractTotal');
  if (invTotalInput && !invTotalInput.dataset.manual) {
    invTotalInput.value = total.toFixed(2);
    updateInvoicePreview();
  }
}

function addQuoteItem() {
  quoteItems.push({ desc: 'New Tender Item / Task Deliverable', qty: 1, unit: 'Nos', rate: 1000.00 });
  renderQuoteItemsTable();
}

function removeQuoteItem(idx) {
  if (quoteItems.length <= 1) return;
  quoteItems.splice(idx, 1);
  renderQuoteItemsTable();
}

function updateQuotePreview() {
  const form = getLetterFormData();
  setTxt('prevQuoteCompName', form.compName);
  setTxt('prevQuoteCompReg', 'Reg No: ' + form.compReg);
  setTxt('prevQuoteCompTin', 'TIN: ' + form.compTin);
  setTxt('prevQuoteCompPhone', form.phone);
  setTxt('prevQuoteCompEmail', form.email);
  setTxt('prevQuoteValidity', document.getElementById('quoteValidity')?.value || '90 Calendar Days');
  setTxt('prevQuoteDelivery', document.getElementById('quoteDelivery')?.value || '30 Calendar Days from PO');
  setTxt('prevQuoteSignatory', form.signatory);
  setTxt('prevQuoteSignComp', form.compName);
}

// TAB 5: BOQ SPREADSHEET & RATE ANALYSIS
let boqItems = [
  { code: '1.01', trade: 'Preliminaries', desc: 'Site mobilization, safety compliance & signage', unit: 'Lot', qty: 1, mat: 5000, lab: 3000, margin: 15 },
  { code: '2.01', trade: 'Materials & Supply', desc: 'Specified materials procurement & warehouse staging', unit: 'Nos', qty: 10, mat: 2200, lab: 400, margin: 15 },
  { code: '3.01', trade: 'Installation', desc: 'Installation, calibration & integration works', unit: 'Days', qty: 6, mat: 800, lab: 1800, margin: 15 },
  { code: '4.01', trade: 'Handover & QA', desc: 'Comprehensive testing, QA certification & documentation', unit: 'Lot', qty: 1, mat: 1200, lab: 2500, margin: 15 }
];

function renderBoqTable() {
  const tbody = document.getElementById('boqInputTable');
  const prevTbody = document.getElementById('prevBoqTableBody');
  if (!tbody || !prevTbody) return;
  tbody.innerHTML = ''; prevTbody.innerHTML = '';
  let totalWithMargin = 0;

  boqItems.forEach((b, idx) => {
    const directCost = (b.mat || 0) + (b.lab || 0);
    const unitRate = directCost * (1 + ((b.margin || 0) / 100));
    const itemTotal = unitRate * (b.qty || 0);
    totalWithMargin += itemTotal;

    const tr = document.createElement('tr');
    tr.className = 'border-b border-hairline/60';
    tr.innerHTML = `<td class="py-1.5 pr-1 w-14"><input type="text" value="${b.code}" oninput="boqItems[${idx}].code=this.value; updateBoqPreview();" class="w-full text-xs p-1 border border-hairline rounded font-mono"></td><td class="py-1.5 px-1"><input type="text" value="${b.desc}" oninput="boqItems[${idx}].desc=this.value; updateBoqPreview();" class="w-full text-xs p-1 border border-hairline rounded"></td><td class="py-1.5 px-1 w-14"><input type="text" value="${b.unit}" oninput="boqItems[${idx}].unit=this.value; updateBoqPreview();" class="w-full text-xs p-1 border border-hairline rounded text-center"></td><td class="py-1.5 px-1 w-14"><input type="number" value="${b.qty}" min="1" oninput="boqItems[${idx}].qty=parseFloat(this.value)||0; renderBoqTable();" class="w-full text-xs p-1 border border-hairline rounded text-center"></td><td class="py-1.5 px-1 w-18"><input type="number" value="${b.mat}" min="0" oninput="boqItems[${idx}].mat=parseFloat(this.value)||0; renderBoqTable();" class="w-full text-xs p-1 border border-hairline rounded text-right"></td><td class="py-1.5 px-1 w-18"><input type="number" value="${b.lab}" min="0" oninput="boqItems[${idx}].lab=parseFloat(this.value)||0; renderBoqTable();" class="w-full text-xs p-1 border border-hairline rounded text-right"></td><td class="py-1.5 pl-1 w-8 text-center"><button type="button" onclick="removeBoqItem(${idx})" class="text-rose-600 font-bold hover:text-rose-800">&times;</button></td>`;
    tbody.appendChild(tr);

    const prevTr = document.createElement('tr');
    prevTr.className = 'border-b border-hairline/60 text-xs';
    prevTr.innerHTML = `<td class="py-2 pr-2 font-mono text-slate-500">${b.code}</td><td class="py-2 pr-2 font-medium text-ink">${b.desc}</td><td class="py-2 px-2 text-center text-slate">${b.unit}</td><td class="py-2 px-2 text-center text-slate">${b.qty}</td><td class="py-2 px-2 text-right font-mono">${fmtMvr(unitRate)}</td><td class="py-2 pl-2 text-right font-mono font-semibold text-ink">${fmtMvr(itemTotal)}</td>`;
    prevTbody.appendChild(prevTr);
  });

  const gst = totalWithMargin * 0.08;
  const grandTotal = totalWithMargin + gst;
  setTxt('prevBoqSubtotal', 'MVR ' + fmtMvr(totalWithMargin));
  setTxt('prevBoqGst', 'MVR ' + fmtMvr(gst));
  setTxt('prevBoqGrandTotal', 'MVR ' + fmtMvr(grandTotal));
}

function addBoqItem() {
  boqItems.push({ code: (boqItems.length + 1) + '.01', trade: 'General', desc: 'Additional Scope item', unit: 'Nos', qty: 1, mat: 1000, lab: 500, margin: 15 });
  renderBoqTable();
}

function removeBoqItem(idx) {
  if (boqItems.length <= 1) return;
  boqItems.splice(idx, 1);
  renderBoqTable();
}

function updateBoqPreview() {
  const form = getLetterFormData();
  setTxt('prevBoqCompName', form.compName);
  setTxt('prevBoqCompReg', 'Reg No: ' + form.compReg);
  setTxt('prevBoqSignatory', form.signatory);
  setTxt('prevBoqSignComp', form.compName);
}

// TAB 6: MIRA TAX INVOICING & PROGRESS CLAIMS
function updateInvoicePreview() {
  const form = getLetterFormData();
  const invTotal = parseFloat(document.getElementById('invContractTotal')?.value) || 57500.00;
  const stage = document.getElementById('invMilestoneStage')?.value || 'advance';
  const invNum = (document.getElementById('invNumber')?.value || 'INV-2026-089').trim();

  let pct = 0.15, stageTitle = '15% Advance Mobilization Payment Claim';
  if (stage === 'progress1') { pct = 0.35; stageTitle = '35% Milestone 1 Interim Completion Claim'; }
  else if (stage === 'progress2') { pct = 0.35; stageTitle = '35% Milestone 2 Substantial Completion Claim'; }
  else if (stage === 'retention') { pct = 0.15; stageTitle = '15% Final Handover & Retention Release Claim'; }

  const stageBase = (invTotal / 1.08) * pct;
  const stageGst = stageBase * 0.08;
  const stageTotal = stageBase + stageGst;
  const dateStr = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });

  setTxt('prevInvCompName', form.compName);
  setTxt('prevInvCompReg', 'Reg: ' + form.compReg);
  setTxt('prevInvCompTin', 'MIRA TIN: ' + form.compTin);
  setTxt('prevInvCompPhone', form.phone);
  setTxt('prevInvCompEmail', form.email);
  setTxt('prevInvNum', invNum);
  setTxt('prevInvDate', dateStr);
  setTxt('prevInvAgencyName', window.BID_CONTEXT?.agency || 'Public Authority');
  setTxt('prevInvAgencyLoc', window.BID_CONTEXT?.submissionLocation || 'Male, Maldives');
  setTxt('prevInvStageDesc', stageTitle + ' — ' + (window.BID_CONTEXT?.titleEn || 'Tender Contract'));
  setTxt('prevInvTaxableBase', 'MVR ' + fmtMvr(stageBase));
  setTxt('prevInvGst', 'MVR ' + fmtMvr(stageGst));
  setTxt('prevInvTotalPayable', 'MVR ' + fmtMvr(stageTotal));
  setTxt('prevInvSignatory', form.signatory);
  setTxt('prevInvSignComp', form.compName);
}

// 1 FREE BID PACKAGE SUBMISSION & HOOKS85 GATEWAY
const currentNoticeId = String(window.BID_CONTEXT?.noticeId || '');

function getFreeBidNoticeId() {
  try { return localStorage.getItem('khulaasaa_free_bid_notice_id') || ''; } catch (e) { return ''; }
}

function isEligibleForFreeBid() {
  const saved = getFreeBidNoticeId();
  return (!saved || saved === currentNoticeId);
}

function claimFreeBidNotice() {
  try {
    if (!localStorage.getItem('khulaasaa_free_bid_notice_id') && currentNoticeId) {
      localStorage.setItem('khulaasaa_free_bid_notice_id', currentNoticeId);
      updateFreeBidUI();
    }
  } catch (e) {}
}

function updateFreeBidUI() {
  const saved = getFreeBidNoticeId();
  const bannerDesc = document.getElementById('freeBidBannerDesc');
  const bannerStatus = document.getElementById('freeBidNoticeStatus');
  const isPaid = window.SERVER_IS_PAID === true;

  if (isPaid) {
    if (bannerDesc) bannerDesc.innerText = 'Unlimited Bids Active: Your hooks85 Pro subscription unlocks unlimited unwatermarked submissions across all tenders.';
    if (bannerStatus) bannerStatus.innerText = 'hooks85 Pro Active';
    document.querySelectorAll('.tab-free-badge').forEach(b => {
      b.innerText = 'Pro Unlocked';
      b.className = 'px-1.5 py-0.2 rounded font-semibold bg-emerald-100 text-emerald-800 tab-free-badge';
    });
    return;
  }

  if (!saved || saved === currentNoticeId) {
    if (bannerDesc) bannerDesc.innerText = `You have 1 free bid package credit! Create, customize, and export all 6 documents for Notice #${currentNoticeId} at zero cost.`;
    if (bannerStatus) bannerStatus.innerText = `1 Free Bid Active (#${currentNoticeId})`;
    document.querySelectorAll('.tab-free-badge').forEach(b => {
      b.innerText = '1 Free Bid';
      b.className = 'px-1.5 py-0.2 rounded font-semibold bg-emerald-50 text-emerald-800 tab-free-badge';
    });
  } else {
    if (bannerDesc) bannerDesc.innerText = `Your 1 free bid was used for Notice #${saved}. Subscribe to hooks85 Tender ERP for unlimited bids and team collaboration.`;
    if (bannerStatus) bannerStatus.innerText = `Free Bid Used (#${saved})`;
    document.querySelectorAll('.tab-free-badge').forEach(b => {
      b.innerText = 'hooks85 Pro';
      b.className = 'px-1.5 py-0.2 rounded font-semibold bg-amber-50 text-amber-800 tab-free-badge';
    });
  }
}

function downloadDocument(docType) {
  const isPaid = window.SERVER_IS_PAID === true;
  if (docType === 'letters') {
    activePrintDocId = 'printableLetterContainer';
    prepareAndPrint();
    return;
  }
  const docMap = {
    'proposal': 'printableProposalContainer',
    'quote': 'printableQuoteContainer',
    'boq': 'printableBoqContainer',
    'invoice': 'printableInvoiceContainer'
  };

  if (isPaid || isEligibleForFreeBid()) {
    if (!isPaid && isEligibleForFreeBid()) claimFreeBidNotice();
    activePrintDocId = docMap[docType] || 'printableLetterContainer';
    prepareAndPrint();
  } else {
    openHooks85Modal(docType);
  }
}

function openHooks85Modal(docType) {
  const modal = document.getElementById('hooks85DownloadModal');
  const docTitleEl = document.getElementById('hooks85ModalDocType');
  const expEl = document.getElementById('hooks85ModalExplanation');
  const saved = getFreeBidNoticeId();
  if (docTitleEl) {
    const names = {
      'proposal': 'Official Technical Proposal',
      'quote': 'Official Commercial Price Quotation',
      'boq': 'Itemized BOQ Spreadsheet & Rate Analysis',
      'invoice': 'MIRA GST Tax Invoice & Progress Claim'
    };
    docTitleEl.innerText = names[docType] || 'Tender Submission Package';
  }
  if (expEl && saved && saved !== currentNoticeId) {
    expEl.innerText = `You have already created your 1 free bid package for Notice #${saved}. Subscribe to hooks85 Tender ERP to unlock unwatermarked dossiers, BOQ exports, and MIRA invoices for Notice #${currentNoticeId}.`;
  }
  if (modal) modal.classList.remove('hidden');
}

function closeHooks85Modal() {
  const modal = document.getElementById('hooks85DownloadModal');
  if (modal) modal.classList.add('hidden');
}

async function activateTrialAndDownload(docType) {
  const btn = document.getElementById('btnHooks85Trial');
  if (btn) btn.innerText = 'Activating Trial...';
  try {
    const res = await fetch('/api/auth/start-trial', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      window.SERVER_IS_PAID = true;
      updateFreeBidUI();
      closeHooks85Modal();
      downloadDocument(docType || 'proposal');
      return;
    }
  } catch (err) {}
  window.SERVER_IS_PAID = true;
  updateFreeBidUI();
  closeHooks85Modal();
  downloadDocument(docType || 'proposal');
}

function prepareAndPrint() {
  document.querySelectorAll('.active-print-target').forEach(el => el.classList.remove('active-print-target'));
  const target = document.getElementById(activePrintDocId);
  if (target) target.classList.add('active-print-target');
  window.print();
}

function exportBoqCsv() {
  const isPaid = window.SERVER_IS_PAID === true;
  if (!isPaid && !isEligibleForFreeBid()) {
    openHooks85Modal('boq');
    return;
  }
  if (!isPaid && isEligibleForFreeBid()) claimFreeBidNotice();
  let csv = 'Code,Trade,Description,Unit,Qty,Material_Rate,Labour_Rate,Margin_Pct,Unit_Rate,Total_Amount\n';
  boqItems.forEach(b => {
    const directCost = (b.mat || 0) + (b.lab || 0);
    const unitRate = directCost * (1 + ((b.margin || 0) / 100));
    const itemTotal = unitRate * (b.qty || 0);
    csv += `"${b.code}","${b.trade}","${b.desc.replace(/"/g, '""')}","${b.unit}",${b.qty},${b.mat},${b.lab},${b.margin},${unitRate.toFixed(2)},${itemTotal.toFixed(2)}\n`;
  });
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `BOQ_${window.BID_CONTEXT?.referenceNumber || window.BID_CONTEXT?.noticeId || 'Tender'}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// INITIALIZATION
document.addEventListener('DOMContentLoaded', function() {
  let data = null;
  try {
    const saved = localStorage.getItem('khulaasaa_bidder_company');
    if (saved) data = JSON.parse(saved);
  } catch (e) {}

  const s = (id, val) => { const el = document.getElementById(id); if (el && !el.value) el.value = val; };
  s('letCompName', data?.name || window.SERVER_PROFILE?.company_name || 'Mai & Emi Investments Pvt Ltd');
  s('letCompReg', data?.reg || window.SERVER_PROFILE?.registration_number || 'C04812021');
  s('letCompTin', data?.tin || window.SERVER_PROFILE?.tin_number || '1130267');
  s('letSignatory', data?.signatory || window.SERVER_PROFILE?.managing_director_name || 'Mohamed Ali (Managing Director)');
  s('letPhone', data?.phone || window.SERVER_PROFILE?.phone || '+960 778 1557');
  s('letEmail', data?.email || window.SERVER_PROFILE?.email || 'procurement@company.mv');

  updateLetterContent();
  updateProposalPreview();
  renderQuoteItemsTable();
  updateQuotePreview();
  renderBoqTable();
  updateBoqPreview();
  updateInvoicePreview();
  updateFreeBidUI();
});
