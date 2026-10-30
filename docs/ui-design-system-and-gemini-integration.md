# Khulaasaa UI Design System — Canonical Theme & Reusable Components

**Branch:** `fix/auth-registration-and-page-performance`
**Purpose:** Make every page use one shared visual system and keep the UI redesign independent of application/business logic.

## Existing canonical theme (verified in `static/css/base.css`)

These are the current theme tokens, not colors invented from the mockup:

| Token | Current value | Usage |
|---|---|---|
| `--ink` | `#10222E` | Primary text, primary buttons, active nav |
| `--ink-soft` | `#1B3140` | Hover/secondary dark surface |
| `--paper` | `#F6F3EC` | Main page background |
| `--paper-soft` | `#EFEBE1` | Soft surface, filter background |
| `--lagoon` | `#2F7C74` | Primary brand accent, selected indicators |
| `--flag` | `#B3432B` | Breaking/news alert |
| `--gold` | `#C89B3C` | Secondary highlight |
| `--slate` | `#5B6572` | Secondary text |
| `--hairline` | `#D9D3C4` | Borders/dividers |
| `--hairline-dark` | `#2A3E4C` | Dark-surface border |

Typography currently uses Inter for Latin UI and Noto Sans Thaana for Dhivehi. Preserve the fonts and existing brand logo/mark. Do not replace the current Khulaasaa identity with the blue palette in the concept mockup.

## Theme centralization work required

The app already has a shared CSS entry point: `static/css/style.css` imports `base.css`, `components.css`, and `modals.css`. `templates/base.html` loads that entry point. However, page templates still contain one-off inline styles and utility-like classes with inconsistent component styling.

Make these shared files the canonical system:
- `static/css/base.css`: design tokens, reset, typography, layout primitives.
- `static/css/components.css`: reusable component styles (buttons, pills, cards, badges, filter drawer, nav).
- `static/css/modals.css`: modal component styles only.
- `static/css/icons.js` (or an existing shared icon module): icon registry.
- `templates/components/`: reusable Jinja components/macros for shared app bar, filter controls, ad slots, cards, and bottom navigation.

Do not add page-specific duplicate tokens or a second CSS framework. Avoid runtime Tailwind/CDN dependencies. Any remaining legacy classes should map to the same tokens.

## Component standards

### Page surfaces
- Every page uses `--paper` as the base canvas.
- Raised cards/panels use white or `--paper-soft`, a 1px `--hairline` border, and consistent radius/shadow.
- Main content cards remain structurally unchanged in this UI pass; do not redesign article/listing content cards.

### Buttons and pills
- Primary button: `--ink` background, white text, shared hover/focus states.
- Secondary button: white/soft background, `--ink` text, `--hairline` border.
- Filter pills are rectangular with rounded corners (not capsule/pill-shaped): use one shared radius token, target 6–8px. Same height, typography, horizontal padding, border, hover, focus-visible, selected, and disabled treatment across all pages.
- Selected filter: `--lagoon` or `--ink` fill with sufficient contrast; choose one treatment globally and use it consistently. Preferred accent: `--lagoon`.
- Do not hardcode category colors inline. Categories use a shared semantic color map / tokenized legend.

### Filter row and expandable filter panel
- Keep visible category/topic filter pills in a horizontally scrollable, single row by default on mobile; preserve the current content cards.
- A filter trigger is adjacent to the pills, with a clear chevron-down when collapsed and chevron-up when expanded. Accessible name and `aria-expanded` must match state.
- Desktop uses the same trigger/expand behavior; the expanded panel can lay out filters in columns.
- Filters are not just controls: the visible pills are also the **legend** for category/narrative colors. Use a shared category registry (stable id, label, color token, icon key if applicable). The same registry drives pill labels, selected state, expanded filter options, card/category badges, and legend key. Avoid separately authored color/label lists.
- Include a legend label or accessible description when color meaning is not self-evident. Never rely on color alone: include readable category text and/or a shape/icon cue.
- The expanded panel should show the active values, reset/clear option, and an apply action when filters are staged. Existing immediate-link filters may remain immediate if that is current behavior; do not silently change filtering semantics while styling.

### Icons
- Centralize icons in a single registry/library. Prefer inline SVG icon definitions with a consistent 20/24px viewBox, stroke width, and currentColor.
- Use exact existing icon designs where already present; migrate duplicated inline SVGs into the registry without changing behavior.
- Components request icons by stable keys (e.g. `search`, `chevron-down`, `chevron-up`, `filter`, `home`, `bookmark`, `bell`, `user`, `menu`, `calendar`, `eye`, `external-link`). Unknown keys should fail gracefully or use a generic fallback.
- Do not use emoji as icons. Maintain accessible labels for icon-only buttons and mark decorative SVGs `aria-hidden=true`.

### App shell and advertising
- Keep the Khulaasaa logo and current page title in the app bar; remove the redundant product title and search field per agreed layout.
- Desktop: main web ad slot above the app bar; site navigation integrated within app bar. Mobile: thin main ad below the bottom navigation, respecting safe-area insets and never covering controls/content.
- Keep existing connected Telegram/Viber badges and avatar/account actions.
- Ad component receives a validated placement/view model; it does not select campaigns or compute eligibility in the template.

## Category/filter legend data contract

Use one server-provided registry, e.g.:
```python
{
  "id": "ras-male",
  "label": "Ras Malé",
  "color_token": "category-civic",
  "icon_key": "landmark",
  "active": False,
  "count": 12
}
```
Color token maps to a CSS variable; do not accept arbitrary CSS colors from user input. For story topic/tag filters, preserve existing stable ids and query parameter contracts. Category counts may be omitted when not available.

## Separation from business logic

- Templates/macros only render passed view models.
- Client-side behavior toggles drawer, manages accessible focus/state, and submits filters; it cannot decide permission, ad eligibility, paid status, or business policy.
- API integration remains Gemini's task: connect existing API endpoints to component contracts, without changing the service/domain behavior as part of visual styling.
- Keep editorial moderation and ad management as separate feature modules, even if they share the app shell/components.

## Acceptance criteria / verification

1. Audit all pages for colors, backgrounds, buttons, filter pills, and icon duplicates; replace page-level overrides with shared tokens/classes.
2. Confirm `base.html` loads the shared CSS once and no page adds a competing theme.
3. Confirm filter pills show the category legend and selected state consistently, and the expand chevron flips with `aria-expanded`.
4. Test mobile widths (320px, 360px, 390px, 430px) and desktop (1024px, 1280px, 1440px); no horizontal page overflow.
5. Test keyboard navigation, focus-visible, contrast, reduced motion, and accessible icon-only controls.
6. Run existing UI/auth/API tests. Do not claim tests pass unless executed.
7. Keep story cards, current card information hierarchy, Telegram/Viber connection indicators, avatar menu, and account functionality intact.
