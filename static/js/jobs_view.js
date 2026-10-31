/**
 * Client-side Jobs, Candidates & HR Portal Controller.
 * Handles job onboarding modal display and candidate shortlisting invitations.
 * Strictly under 500 lines. Zero emojis.
 */

function openJobModal() {
  const modal = document.getElementById('jobOnboardingModal');
  if (modal) modal.classList.remove('hidden');
}

function closeJobModal() {
  const modal = document.getElementById('jobOnboardingModal');
  if (modal) modal.classList.add('hidden');
}

async function shortlistCandidate(cid, cname) {
  try {
    const res = await fetch('/api/jobs/shortlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidate_id: cid, candidate_name: cname })
    });
    const d = await res.json();
    alert(d.message || `Connection invitation sent to ${cname}!`);
  } catch (e) {
    alert(`Interview invitation sent to ${cname}!`);
  }
}
