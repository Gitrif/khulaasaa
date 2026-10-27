# Khulaasaa CSS Refactor Report

**Branch:** `refactor/css-bundle-cleanup`  
**Scope:** CSS loading, shared stylesheet ownership, and safe consolidation readiness  
**Status:** Source-level refactor applied; browser/visual regression tests not run in this environment.

## Summary

The global stylesheet was being loaded through two paths:

- `templates/base.html` linked `base.css`, `components.css`, and `modals.css` directly.
- The same page also linked `style.css`, which imported those files again.
- `style.css` also imported `cv.css` globally, even though `templates/cv_creator.html` already loads it page-specifically.
- `print.css` was linked once with `media="print"` and imported again through `style.css`. The file contains screen rules for `.page-sheet` as well as print-only rules, so it must remain available outside print media unless that screen rule is moved elsewhere.

## Changes applied

1. **One global CSS entry point:** `templates/base.html` now links only `/static/css/style.css` for stylesheets.
2. **Shared layers loaded once:** `style.css` remains the single global entry point and imports `base.css`, `components.css`, `modals.css`, and `print.css` once each.
3. **CV CSS page-scoped:** Removed the global `cv.css` import. `templates/cv_creator.html` retains its explicit `/static/css/cv.css` link in `extra_head`.
4. **Print behavior preserved:** `print.css` remains in the global bundle because `.page-sheet` has non-print styling in addition to its `@media print` rules. The redundant direct `media="print"` link was removed.

## Files changed

| File | Change |
|---|---|
| `templates/base.html` | Removed duplicate direct links to base/components/modals/print; retained the single global bundle |
| `static/css/style.css` | Removed the global CV stylesheet import |
| `docs/css_refactor_report.md` | This report |

## Source-level measurements before the change

Approximate source sizes observed on `main` before refactoring:

| File | Lines | Bytes | Intended role |
|---|---:|---:|---|
| `base.css` | 414 | 14,448 | Tokens, reset, typography, utility primitives |
| `components.css` | 1,282 | 37,239 | Shared navigation, cards, badges, buttons, footer and feed components |
| `modals.css` | 178 | 5,225 | Modal and dialog styles |
| `cv.css` | 651 | 15,377 | CV editor and four CV themes |
| `print.css` | 136 | 3,732 | Paper sheet screen styling plus print/PDF rules |
| `style.css` | 10 | 434 | Global stylesheet entry point |

These are source file sizes, not measured transfer-size or page-load improvements. The change removes duplicate stylesheet requests/processing and prevents CV theme rules from being downloaded through the global import on non-CV pages; actual network savings should be confirmed in browser DevTools.

## Reuse and duplication findings

### Keep as shared primitives

- Design tokens in `:root` for ink, paper, lagoon, flag, gold, slate and borders.
- Shared utility classes in `base.css`.
- Shared card, badge, button, source-label, navigation and footer styles in `components.css`.
- Modal overlay/dialog foundations in `modals.css`.
- CV-specific paper, timeline, photo and theme styles in `cv.css`.

### Consolidation candidates that need visual regression coverage

- `components.css` has repeated `.story-card`, `.story-card:hover`, `.card-headline`, `.card-time`, `.card-sources-line`, `.card-eyebrow`, `.mobile-bottom-nav`, `.desktop-nav-menu`, and footer selectors. Some later declarations are responsive or intentional overrides (including narrow-screen rules with `!important`), so they should not be deleted simply because a selector appears more than once.
- `cv.css` repeats `.cv-floating-actions` in a base rule and a desktop media query; the desktop rule contains legitimate breakpoint-specific differences.
- `print.css` repeats `.page-sheet` inside `@media print`; the second declaration intentionally overrides the screen presentation for printing.
- `modals.css` relies heavily on `!important`. Reduce these only after confirming which rules win and checking authentication, alert, filter, Telegram and Viber dialogs.
- Several utility selectors in `base.css` overlap conceptually. Compare declarations and usage before consolidating: similar names can have different colors, radii or priority.

## Recommended next stage

1. Run template/static-asset reference checks and browser checks for home/news, bids, jobs, rentals, obituaries, CV creation/preview, corporate paper sheets and bid document printing.
2. Capture computed styles/screenshots at mobile widths (including 270–360px), tablet and desktop before merging any duplicate component rules.
3. Consolidate repeated feed-card styles into one canonical base rule plus explicit modifiers (for example, compact/featured variants) only after mapping every template that uses them.
4. Keep the four CV themes visually distinct; extract only demonstrably identical primitives.
5. Reduce `!important` by correcting selector ownership/specificity, not by deleting declarations wholesale.
6. Measure actual CSS requests, transferred bytes and rendering behavior before claiming a performance percentage.

## Verification status

- **Performed:** GitHub source inspection; stylesheet import/reference review; patch-level review of the two changed files.
- **Not performed:** pytest, application startup, browser screenshots, responsive interaction tests, PDF/print regression tests, or live network measurements.
- **Safety:** No database, ingestion, production configuration or deployment changes were made.

## Outcome

The duplicate global stylesheet loading is corrected, CV theme CSS is limited to the CV page that explicitly requests it, and print/paper styles remain available to preserve current screen and print behavior. Remaining selector consolidation is intentionally identified as a follow-up requiring visual regression coverage rather than a blind bulk deletion.
