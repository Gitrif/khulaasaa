/**
 * Client-side Jobs & Careers Controller.
 * Handles job onboarding modal display and dismissed states.
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
