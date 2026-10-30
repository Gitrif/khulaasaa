# Gemini Handoff — UI/API Integration, Logic Separation, and Legacy Removal

**Repository:** `Gitrif/khulaasaa`  
**Branch:** `fix/auth-registration-and-page-performance`  
**Primary rule:** This is an API integration and architecture task, not permission to redesign business behavior.

## A. Required architecture

Separate presentation from business logic with strict dependency direction:

```
Jinja templates + CSS + browser JS
              |
              v
Presentation routers (HTTP only)
              |
              v
Application services (use cases)
              |
              v
Domain policies / entities
              |
              v
Repositories (database persistence)
```

### UI responsibilities
- Render passed view models.
- Collect user input and call documented API endpoints.
- Manage presentation state only: open/closed drawers, loading, selected tab, temporary form values.
- Never decide user permissions, ownership, payment state, editorial approval, ad eligibility, quota, subscription entitlements, or notification authorization.
- Never access the database or call bot-provider APIs.

### Router responsibilities
- Parse/validate HTTP input and authentication context.
- Call one application service/use case.
- Map service results/errors into stable response schemas or template view models.
- No SQL, business rules, direct provider broadcast, or duplicated permission logic.

### Service responsibilities
- Enforce authorization and ownership.
- Own workflows and state transitions.
- Validate business invariants.
- Coordinate repositories and outbox/provider services.
- Be callable from web UI, API, bot/webhook and background worker without depending on templates.

### Repository responsibilities
- Persistence only. No permission decisions, workflow transitions, HTTP, template rendering, or outbound notifications.

## B. API connection contracts Gemini must implement

First inspect current route registrations and schemas. Reuse existing stable endpoints where correct. Do not invent endpoints in the browser and do not make UI call undocumented legacy endpoints. Create a small API contract document/OpenAPI schemas for these feature groups.

### 1. Shared response convention

Success:
```json
{"status":"ok","data":{}}
```
Failure:
```json
{"status":"error","error":{"code":"VALIDATION_ERROR","message":"Please check the submitted fields","fields":{}}}
```

Use existing response conventions if already established; do not introduce incompatible envelope shapes without migrating all clients. Never expose exception traces or internal provider/database details.

### 2. Authentication/account UI
- Login: use the canonical email/password contract already expected by the auth service (the current modal sends `email` and `password`; do not restore the legacy `identifier` payload).
- Registration: call the canonical registration endpoint; handle duplicate email (409), validation errors, and rate limiting.
- Session: use server-authenticated session state; never infer authentication from localStorage.
- Account profile: read/update the current user's profile through authenticated account routes.
- Channel status: GET the current account's linked Telegram/Viber status; linking must use verified provider flows, never a browser-supplied provider ID.
- Alert preferences: GET/PUT the user's own preferences; verified identity and notification opt-in remain separate concepts.
- Notifications: GET current user's notifications and unread count; mark-read through authenticated endpoint.
- Logout: POST server-side session logout and refresh the shell state.
- Preserve public bot access without web registration. Public bot functionality must not be gated by web-account session.

### 3. Editorial UI (editor-only)
Suggested stable service-backed operations:
- `GET /api/editorial/queue` — paginated queue and summary counts.
- `GET /api/editorial/items/{id}` — item, source references, tags, audit history.
- `POST /api/editorial/items/{id}/approve` — approval action.
- `POST /api/editorial/items/{id}/reject` — rejection with reason.
- `POST /api/editorial/items/{id}/preview` — preview intended distribution, no send.
- `POST /api/editorial/items/{id}/publish` — enqueue publication after explicit authorization.
- All endpoints require editor permissions and enforce state transition rules in editorial service.
- The UI must distinguish draft, pending, approved, scheduled, published, rejected, failed.
- Never use an in-memory Python global as the durable editorial queue. Persist queue/workflow state and audit actions.

These are target contracts; first reconcile them with existing route names and migrate clients. Do not add duplicate aliases that implement the same use case.

### 4. Advertising UI
Public ad serving:
- `GET /api/ads?placement=web_feed_card&section=news` — read-only eligible ad response; server decides eligibility. Return no internal campaign data.
- Impression/click tracking should use dedicated signed/opaque event IDs and server-side deduplication; never let the browser increment arbitrary campaign IDs/counters.

Advertiser portal (authenticated, ownership scoped):
- `GET /api/advertiser/campaigns`
- `POST /api/advertiser/campaigns`
- `GET /api/advertiser/campaigns/{campaign_id}`
- `PATCH /api/advertiser/campaigns/{campaign_id}`
- `POST /api/advertiser/campaigns/{campaign_id}/submit`
- `POST /api/advertiser/campaigns/{campaign_id}/pause`
- `POST /api/advertiser/campaigns/{campaign_id}/resume`
- `GET /api/advertiser/campaigns/{campaign_id}/report`
- `POST /api/advertiser/campaigns/{campaign_id}/assets`

Editor ad operations:
- review/approve/reject, quota/budget administration, billing reconciliation and broadcast confirmation remain editor-only.
- Campaign ownership must be enforced in service/repository queries, not hidden UI controls.
- Creative edits to a live/approved campaign trigger re-review.
- Web placements and Telegram/Viber distribution are separate inventory/delivery channels.

Do not expose the existing unguarded campaign creation or broadcast operations to public callers. Audit `routers/api_ads.py` and either secure/migrate/remove its management/broadcast endpoints. Public ad retrieval can remain public but read-only.

### 5. Filters, page content and cards
- Filters remain server-backed using current query parameter names and values.
- UI reads available category/tag/topic metadata from the page view model or a single read-only filter metadata endpoint.
- The same category registry supplies visible filter pills, expanded filter panel, legend markers, and story category labels.
- Keep current story/content card markup and hierarchy. Do not replace it with a new card design.
- Pagination and sorting must preserve current semantics.

### 6. Ad placement API view model
The template should receive only a renderable ad slot object, e.g.:
```json
{
  "placement": "mobile_feed_card",
  "creative": {
    "headline": "Example sponsored message",
    "body": "Short advertiser copy",
    "image_url": "/media/ads/asset-random.webp",
    "image_alt": "Product display",
    "destination_url": "https://advertiser.example"
  },
  "label": "Sponsored",
  "tracking_event_id": "opaque-signed-token"
}
```
No campaign selection or eligibility logic in Jinja/JS. Render escaped text. Do not use Jinja `safe` for advertiser HTML.

## C. Legacy method retirement — mandatory inventory before deletion

Search all routes, templates, JavaScript, tests, and bot handlers for:
- duplicate login/register/session implementations;
- localStorage-based authentication or channel-connected badges;
- browser-supplied Telegram/Viber identity IDs;
- old Telegram/Viber linking endpoints not backed by provider verification;
- direct campaign create/update/broadcast endpoints without auth;
- duplicate filter arrays/inline category colors;
- inline SVG duplicates and emoji icons;
- template-level database/service calls;
- route handlers containing SQL or direct provider sends;
- in-memory editorial workflow state;
- old HTML ad creative rendering with `safe`.

For every legacy method:
1. Identify callers and behavior.
2. Select the single canonical service/API method.
3. Migrate all callers and tests.
4. Add a regression test proving the old behavior still works through the canonical path.
5. Remove the legacy method, route, JS function, template branch, or duplicate data source.
6. Confirm no references remain with repository-wide search.
7. Document removed route/function names and any compatibility redirect/deprecation period.

Do not delete a method merely because it looks old. Do not keep two implementations “temporarily” without a removal issue and deadline. Do not create parallel API routes for the same use case.

## D. UI-specific current work already committed on this branch

- Central design tokens expanded in `static/css/base.css`.
- Shared control/filter styles updated in `static/css/components.css`.
- Main page filter trigger now has `aria-expanded`, `aria-controls`, and a chevron that can rotate when expanded.
- Shared SVG registry added at `static/js/icons.js`, loaded by `templates/base.html`.
- Detailed visual handoff: `docs/khulaasaa-ui-theme-designer-handoff.md`.

The current icon registry is intentionally small; migrate duplicate SVGs gradually and preserve existing icon meaning/behavior. Ensure filter drawer JavaScript actually toggles the `aria-expanded` attribute and hidden state on all relevant pages. Audit the inline handler referenced by `toggleFilterDrawer()`; do not assume it is wired just because the button markup exists.

## E. Required implementation sequence

1. Build a route/template/JS/repository dependency inventory.
2. Establish service layer use cases and typed request/response/view models for account, editorial, ads, and filters.
3. Move SQL and business decisions out of presentation routers/templates.
4. Implement API adapters and connect the UI to canonical contracts.
5. Remove legacy implementations using the migration process above.
6. Consolidate all page templates on the shared theme and components.
7. Migrate duplicate icons into `KhulaasaaIcons`.
8. Keep editorial and advertising as distinct modules.
9. Add tests for anonymous vs member vs advertiser vs editor permissions, ownership isolation, workflow transitions, and API response contracts.
10. Run the complete test suite and lint; verify SQLite and Postgres migrations in a disposable/staging database.
11. Test responsive pages at 320/360/390/430/768/1024/1280/1440 widths and confirm no horizontal overflow.
12. Report exact changed files, deleted legacy methods/routes, test commands/results, and remaining gaps.

## F. Guardrails

- Do not work on scraper architecture during this task.
- Do not change production data or deploy.
- Do not merge this PR.
- Do not change editorial/business rules as part of visual cleanup.
- Do not remove existing content cards, account features, avatar, Telegram/Viber connected indicators, public browsing, or bot access.
- Do not report completion unless the code and tests verify it.
