# Gemini UI implementation instructions — Khulaasaa

## Scope

Continue the responsive UI work in this branch without changing the product architecture or existing story-card design.

Branch: `feat/responsive-filter-dock`
Base: `fix/auth-registration-and-page-performance`
Current PR: https://github.com/Gitrif/khulaasaa/pull/3

## 1. Dhivehi typography: Faruma

- Use **Faruma** as the preferred font for Dhivehi / Thaana text wherever it is rendered.
- The global Thaana selector in `static/css/base.css` now puts `Faruma` first, followed by installed/platform fallbacks and `Noto Sans Thaana`.
- Apply the `font-thaana` class to isolated Dhivehi strings and brand glyphs when the content is not already inside a `dir="rtl"`, `.thaana-title`, or `.thaana-text` region.
- Do not apply Faruma to English UI labels, numbers, dates, or Latin-script content. Keep the English interface typography on Inter.
- **Important font asset check:** inspect `static/fonts/` and the repository for an actual Faruma font file. The CSS stack change alone does not bundle a font. If no Faruma asset exists, source a properly licensed Faruma webfont, verify its licence and format, add it under `static/fonts/`, and declare it with `@font-face` using `font-display: swap`. Do not rename another Thaana font to Faruma or assume that users have Faruma installed.
- Test actual Dhivehi strings at mobile and desktop sizes, including mixed Dhivehi/English labels, punctuation, numbers, and RTL alignment. Confirm no clipping, broken joining, or unexpected line-height.

## 2. Janaza navigation icon

- The Janaza / Obituaries item must use a **crescent moon** icon, not a cross, plus sign, or generic religious symbol.
- The mobile navigation icon in `templates/base.html` has been changed to a crescent moon SVG.
- Keep the icon semantically consistent anywhere else the Janaza destination is represented (desktop navigation, page headings, menus, and empty states). Reuse the same simple crescent SVG path or the shared icon registry; do not introduce emoji.
- Preserve the visible label “Janaza” or “Obituaries” according to the existing navigation context.

## 3. Shared responsive filter section

- There must be one shared filter component and one source of filter markup/state, not separate desktop and mobile copies.
- Desktop: the two-row filter section sits directly below the app header and above page content.
- Mobile: the same two-row section is fixed above the mobile bottom navigation. Stack order from top to bottom is:
  1. scrollable page content,
  2. shared two-row filter dock,
  3. mobile bottom navigation,
  4. bottom safe-area inset.
- Keep the filter rows compact and equal in height. Keep horizontal scrolling for pills. Do not let the filter drawer or pills cause horizontal page overflow.
- Add enough bottom clearance to the page content so the final card is never obscured by the dock.
- Check iOS/Android safe-area insets, 270px–430px widths, tablet breakpoint, desktop, keyboard-open state, and landscape.
- The filter content must be page-aware for News, Tenders, Jobs, Rentals, and Notices. Do not display News-only tags on unrelated pages. Use the page's existing query parameters and backend-supported filters; do not invent routes or query parameters.
- Advanced filters must continue to open/close accessibly, expose `aria-expanded`, and remain usable above the mobile dock.

## 4. Navigation and ads

- Preserve Telegram/Viber connection status, notification controls, and the authenticated user avatar/menu.
- Keep the mobile bottom navigation above the bottom safe-area inset.
- Reserve an actual ad slot beneath the mobile navigation only if the existing ad system supports it. Do not hardcode a fake ad or create an overlapping fixed layer.
- Verify footer links and page content remain reachable when the dock is present.

## 5. Constraints

- Do not redesign, replace, or restyle the existing story cards as part of this task.
- Do not remove working functionality, filters, query parameters, channel badges, avatar behavior, accessibility labels, or guest browsing.
- No native mobile app. This is a responsive web interface.
- Keep FastAPI/Jinja and the existing vanilla CSS/JS approach. No new frontend framework.
- Avoid duplicate CSS rules, duplicate event handlers, inline JS where an existing shared handler is appropriate, and hardcoded page-specific markup copied into multiple templates.
- Do not merge or deploy without explicit approval.

## 6. Required validation and handoff

Before marking complete:

1. Inspect all page templates and identify every Dhivehi/Thaana-rendering location.
2. Verify the Faruma font file is genuinely present, licensed, served with the correct MIME type, and actually loaded in browser devtools. If unavailable, report this explicitly rather than claiming Faruma is active.
3. Verify the crescent moon appears on the Janaza mobile navigation item and any other relevant navigation representation.
4. Test News, Tenders, Jobs, Rentals, and Notices at mobile, tablet, and desktop widths.
5. Test filter selection, query persistence, advanced drawer, keyboard focus, horizontal scrolling, and browser back/forward.
6. Confirm mobile content is not hidden behind the dock and safe-area insets work.
7. Run the existing test suite and lint checks. Fix regressions caused by this change.
8. Report exact files changed, test commands/results, screenshots or viewport evidence, unresolved issues, and commit SHA.

Do not report visual/device testing unless it was actually performed.


---

## 7. Mandatory baseline reconciliation — READ THIS BEFORE EDITING

**Do not start implementing immediately. First establish exactly what is already in this branch and compare it with any work you have already done.** This is a continuation task, not permission to regenerate the UI or replace existing work.

### Known branch baseline and changes already made

The working branch is:

- Branch: `feat/responsive-filter-dock`
- Base branch: `fix/auth-registration-and-page-performance`
- Pull request: https://github.com/Gitrif/khulaasaa/pull/3

The following changes were already committed to this branch during the current implementation pass:

1. **Responsive filter markup** — `templates/index.html`
   - Replaced the old News filter toolbar with a shared two-row filter section.
   - First row: “All stories” plus story/tag filters.
   - Second row: “All topics” plus topic filters.
   - Kept an advanced filter drawer and its toggle.
   - Existing story-card markup was not intentionally changed.

2. **Responsive filter styling** — `static/css/components.css`
   - Added the “Khulaasaa responsive filter dock” CSS section.
   - Desktop: filter section is in normal document flow below the header.
   - Mobile: the same filter section is fixed above the mobile navigation.
   - Added horizontal pill scrolling, compact row dimensions, drawer styling, safe-area-aware navigation height, and bottom body clearance.
   - This is a first implementation pass, not yet proven correct on devices.

3. **Dhivehi font preference** — `static/css/base.css`
   - Changed the existing Thaana font stack to put `Faruma` first, followed by existing fallbacks.
   - This does **not** prove a Faruma webfont asset is bundled or loaded. That must be checked separately.

4. **Brand glyph** — `templates/base.html`
   - Added `font-thaana` to the brand-mark element so its Dhivehi glyph uses the Thaana font stack.

5. **Janaza mobile navigation icon** — `templates/base.html`
   - Replaced the old plus/cross-like icon with a crescent moon SVG.
   - Other Janaza/Obituaries icon occurrences have not yet been comprehensively audited.

6. **Gemini handoff** — `docs/GEMINI_RESPONSIVE_UI_HANDOFF.md`
   - This document contains the intended design, constraints, and validation requirements.

Known commit SHAs from this pass (inspect branch history to confirm exact ancestry and current HEAD):
- Faruma-first CSS stack: `020e05c8454290b3dfb8f7569a48d5572a733988`
- Janaza crescent SVG: `d3d75c709b680d918b89e6862c8cd3c01add89fe`
- Brand glyph font class: `5d25508134969591618b1abf159ab9bfd8228a29`
- Gemini handoff document: `4472f40f4f28656f04aaa3dac95aa45cdc7370e0`

The initial filter markup and CSS commits are also in the branch history; identify their SHAs using Git rather than guessing.

### Phase A — inspect and compare, no edits yet

Before changing any file:

1. Fetch the latest remote state. Confirm you are on `feat/responsive-filter-dock`, and record `git status`, HEAD SHA, and the merge base with `fix/auth-registration-and-page-performance`.
2. Read the complete diff from the base branch to HEAD. Inspect the actual current contents of every changed file. Do not rely only on this handoff document.
3. Inspect your own prior Gemini changes, if any: identify their branch/commit(s), files changed, and current working-tree modifications. Do not discard uncommitted work.
4. Produce a reconciliation table with columns:
   - Requirement
   - Already implemented in this branch (file/line/commit)
   - Present in your prior Gemini work (file/line/commit)
   - Gap, conflict, or regression
   - Proposed minimal action
5. Identify duplicate implementations, competing CSS selectors, duplicate filter markup, duplicate event handlers, conflicting font declarations, icon inconsistencies, and any work that exists in one branch but not the other.
6. **Stop and report the reconciliation before editing if** the Gemini work is on a different branch, contains uncommitted changes, has commits not represented in this branch, or conflicts with these changes. Do not reset, rebase, force-push, cherry-pick, merge, or overwrite anything until the conflict and intended preservation strategy are clear.

### Phase B — implement only verified gaps

After the reconciliation is complete:

1. Preserve all valid work from both sources. Apply only the smallest changes needed to close verified gaps.
2. Do not copy a second filter toolbar into mobile markup. Move/reuse the same DOM component with CSS positioning; there must be one authoritative filter state and one set of controls.
3. Do not append another large CSS block if an existing selector can be corrected cleanly. Consolidate duplicate rules and remove only confirmed dead/duplicate declarations.
4. Do not overwrite whole templates or stylesheets from an older local copy. Make narrow edits against the latest remote content.
5. Preserve all existing route names, query parameter semantics, Jinja context variables, page permissions, guest browsing, story-card includes, notification behavior, Telegram/Viber indicators, and avatar behavior.
6. Verify that page-specific filters are based on actual backend-supported filters and context data. If a page has no filter support, do not invent one; document the gap for a separate backend task.
7. Verify Faruma licensing and the actual font asset before adding it. Do not download or commit a font of uncertain licence. If no valid asset is available, retain the fallback stack and report the blocker.
8. Keep the crescent moon icon consistent and accessible. Use one shared icon definition if the repository already has an icon registry.

### Phase C — validation and evidence

Run the repository's documented test, lint, formatting, and template validation commands. Add focused tests where practical. At minimum:

- Confirm all Jinja templates compile/render with the expected context.
- Confirm the News page filter links preserve the real existing query parameters.
- Confirm filters do not appear twice in the DOM at any viewport.
- Confirm the same filter section is below the header on desktop and docked above navigation on mobile.
- Confirm page content and the final story card remain reachable and are not covered by the dock.
- Confirm the bottom nav and filter dock do not overlap each other, the ad slot, or the safe-area inset.
- Confirm the Janaza crescent SVG is present and no old cross/plus icon remains for that destination.
- Confirm the font actually loads in a browser; CSS declaration inspection alone is insufficient.
- Check desktop, tablet, and narrow mobile widths. Use screenshots or browser automation if available; clearly label any viewport checks that were not performed.
- Run the full existing test suite and report exact command and pass/fail counts.

### Phase D — safe delivery

- Work only on `feat/responsive-filter-dock` after the baseline is reconciled and agreed.
- Commit incremental, reviewable changes with descriptive messages.
- Do not amend or rewrite existing commits.
- Do not force-push.
- Do not merge PR #3, merge into main, deploy, alter production data, or change secrets/environment configuration.
- Before pushing, inspect `git diff`, `git diff --check`, `git status`, and the commit list.
- Final report must distinguish: pre-existing work, Gemini's new changes, tests actually run, visual checks actually performed, unresolved risks, and the resulting commit SHA.

**Priority rule:** protecting the existing repository and preserving valid work takes precedence over finishing quickly. If uncertain whether a change is safe, stop and ask rather than overwrite.
