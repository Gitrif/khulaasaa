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
