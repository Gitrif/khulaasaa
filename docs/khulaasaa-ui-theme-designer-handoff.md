# Khulaasaa UI Design System — Designer Handoff (Canonical)

**Product:** Khulaasaa / ޙުލާސާ  
**Platform:** Responsive web application. No native mobile app.  
**Implementation:** FastAPI + Jinja templates + vanilla JavaScript + modular CSS.  
**Source of truth:** `static/css/base.css`, `static/css/components.css`, `static/css/modals.css`, bundled through `static/css/style.css`.

## 1. Brand character

Khulaasaa is a Maldivian information platform aggregating news, tenders/bids, jobs, notices and public information. The visual language should feel editorial, calm, credible, compact, legible and locally grounded. It is not a generic SaaS dashboard and should not look like a social network.

Preserve the existing logo/brand mark and Dhivehi inscription `ޙުލާސާ`. Do not invent a new logo or replace the palette with blue/purple startup colors.

## 2. Exact canonical palette

These are existing code values in `base.css`; do not approximate or silently change them.

| Token | Hex | Semantic use |
|---|---|---|
| `--ink` | `#10222E` | Primary text, dark navigation, primary actions |
| `--ink-soft` | `#1B3140` | Dark hover/secondary surface |
| `--paper` | `#F6F3EC` | Global page canvas |
| `--paper-soft` | `#EFEBE1` | Toolbar, subtle panel and selected-neutral surfaces |
| `--lagoon` | `#2F7C74` | Brand accent, selected filters, positive status |
| `--flag` | `#B3432B` | Breaking news, urgent/high-priority status |
| `--gold` | `#C89B3C` | Secondary highlight, attention marker |
| `--slate` | `#5B6572` | Secondary text, metadata |
| `--hairline` | `#D9D3C4` | Standard border/divider |
| `--hairline-dark` | `#2A3E4C` | Dark-surface border |

Neutrals: white `#FFFFFF` is reserved for cards and raised surfaces. Do not use pure white as the page canvas. Avoid large saturated color blocks.

### Color semantics
- Ink communicates structure and authority.
- Lagoon communicates brand interaction and selected/positive states.
- Flag is reserved for breaking/urgent information, not decoration.
- Gold is a limited secondary accent.
- Slate is for metadata; maintain readable contrast.
- Category colors are semantic and must be consistent wherever a category appears.

## 3. Typography

- Latin UI: Inter, weights 400, 500, 600, 700, 800.
- Dhivehi/Thaana: Noto Sans Thaana, weights 400, 500, 600, 700.
- Use the existing font stack and RTL handling. Never apply Latin font rules to Thaana content.
- Editorial headline hierarchy should be clear without oversized marketing typography.
- Metadata should remain readable; do not shrink below 11px for essential information.
- Body copy should use comfortable line height (approximately 1.45–1.6).

## 4. Shape, spacing and elevation

Canonical shared tokens now defined in `base.css`:
- Control radius: 7px.
- Card radius: 8px.
- Panel radius: 10px.
- Filter radius: 7px (rectangular rounded corners, never capsule-shaped).
- Control height: 36px.
- Standard control gap: 8px.
- Focus ring: lagoon at low opacity.

Use a 4px spacing rhythm (4, 8, 12, 16, 20, 24, 32). Borders are preferred over heavy shadows. Use shadows sparingly for popovers/dropdowns only. Avoid excessive rounded cards, pill-shaped buttons, glassmorphism and gradients.

## 5. Global page shell

- Main background is always `--paper`.
- Header/app bar uses white or paper surface, with a subtle hairline.
- Keep Khulaasaa logo and the current page title in the app bar.
- Remove redundant app title text and the search field from the agreed app-bar design.
- Desktop navigation belongs inside the app bar.
- Preserve avatar/account menu, notification controls, Telegram connected badge and Viber connected badge.
- Desktop main ad placement is above the app bar.
- Mobile main ad is a thin responsive placement below the bottom navigation; it must not obscure content, safe areas, or controls.
- Preserve existing page content and information hierarchy unless a separate page redesign is explicitly approved.

## 6. Filter system is also the category legend

The filter row has two jobs: navigation/filtering and teaching users the category color key.

- Default state: one horizontally scrollable row of rectangular rounded filter controls.
- Mobile: keep the row compact and visible; no wrapping into multiple rows.
- Desktop: same visual treatment, with room for a wider expanded panel.
- Include a dedicated Filters trigger with chevron-down when collapsed and chevron-up when expanded; update `aria-expanded` and `aria-controls`.
- Expanded panel contains the full filter/topic/tag selection.
- Selected state is lagoon fill + white text, consistently across every page.
- Every category filter shows a text label and its category color marker. Color must never be the only signal.
- The visible row and expanded filter panel must be generated from the same category/tag data registry as category badges/legend. No separately maintained arrays of labels or colors.
- Preserve current query-string semantics and server-side filtering. Styling work must not change filtering behavior.
- Provide clear/reset when multiple filters can be active.

Category registry data shape:
```json
{
  "id": "ras-male",
  "label": "Ras Malé",
  "color_token": "category-civic",
  "icon_key": "landmark",
  "count": 12,
  "active": false
}
```
Color tokens are predefined CSS classes/variables; never accept arbitrary CSS from API/user data.

## 7. Shared controls

All pages must use the same shared component classes:
- Primary action: ink background, white text.
- Secondary action: white background, ink text, hairline border.
- Destructive action: flag semantic, confirm destructive operations.
- Filter pill: rectangular radius 7px, consistent height and padding.
- Badges: compact, readable, semantic color.
- Inputs: white surface, hairline border, ink text, visible focus state.
- Disabled controls: visibly disabled and not interactive.
Do not create page-local variants unless documented as a genuine semantic variant in the component stylesheet.

## 8. Cards and editorial content

**Do not redesign the existing story/content cards in this phase.** Keep their current layout, source attribution, headline hierarchy, timestamps, summaries, action affordances and compactness. The goal is to unify surrounding shell, surfaces, buttons, pills, badges and typography tokens without changing the card information architecture.

Tenders, jobs and notice cards should retain their existing feature-specific fields. Shared card primitives may be reused, but do not force every content type into an identical layout.

## 9. Iconography

A shared registry is now available at `static/js/icons.js` as `window.KhulaasaaIcons`.
- Call `KhulaasaaIcons.svg('filter')` or `KhulaasaaIcons.svg('chevron-down', 'icon-sm')`.
- Registry currently includes: home, bookmark, bell, user, menu, filter, chevron-down, chevron-up, search, calendar, external-link, close.
- Extend the registry rather than duplicating inline SVGs.
- Keep 20/24 viewBox geometry, stroke 1.8, round caps/joins and currentColor.
- Do not use emoji as UI icons.
- Icon-only controls need an accessible label. Decorative SVGs are hidden from assistive technology.
- Do not use arbitrary icon fonts or add a second icon library without approval.

## 10. Responsive breakpoints and behavior

Design and verify at 320, 360, 390, 430, 768, 1024, 1280 and 1440 CSS pixels.
- Mobile first; avoid horizontal page overflow.
- Horizontal scrolling is permitted only inside the filter row or intentionally scrollable content.
- Desktop content max-width remains aligned with the existing 5xl layout unless the page already has a specific wider layout.
- Sticky/fixed bottom navigation and ad placements must account for safe-area insets.
- Touch targets should be approximately 40–44px for primary interactive controls.
- Respect reduced-motion preference.

## 11. Accessibility

- WCAG AA contrast for text and controls.
- Visible keyboard focus.
- Correct button/link semantics.
- `aria-expanded` and `aria-controls` for expandable filters.
- Do not communicate status through color alone.
- Alt text for meaningful images; empty alt for decorative images.
- Maintain Dhivehi RTL direction and mixed-script punctuation.
- Never remove focus outlines without replacement.

## 12. Do not do

- Do not change API routes or business rules while styling.
- Do not put SQL, permission checks, ad selection, campaign status, billing, or workflow decisions in templates or JavaScript.
- Do not add a new frontend framework.
- Do not redesign existing story cards in this phase.
- Do not remove account/avatar/Telegram/Viber status controls.
- Do not reintroduce app title or header search field.
- Do not make filter pills capsule-shaped.
- Do not hardcode colors in page templates.
