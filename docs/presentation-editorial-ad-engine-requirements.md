# Khulaasaa Presentation, Editorial, and Advertising Separation

**Status:** Architecture requirements and repository audit. This is not a claim that the separation has already been implemented.

## Objective

Make the presentation layer replaceable and independently redesignable. UI changes must not change business rules, authorization, campaign state, editorial workflow, persistence, or delivery behavior.

Keep the current FastAPI + Jinja web stack. Do not introduce a frontend framework or mobile app as part of this work.

## Required dependency direction

```
Jinja templates / static CSS / browser JS
             |
             v
Presentation routers (HTTP parsing, response/view models only)
             |
             v
Application services (use cases, validation, permissions, orchestration)
             |
             v
Domain rules (editorial, advertising, account/channel policies)
             |
             v
Repositories / database adapters
```

- Templates must not query databases, decide campaign eligibility, calculate billing/quotas, authorize users, mutate records, or invoke bot providers.
- Browser JavaScript must call documented API endpoints; it must not be a source of truth for role, campaign status, pricing, file validation, identity, or delivery.
- Routers should validate HTTP input, call one application service, and render a view model or stable JSON response. They should not contain SQL, business policy, ad selection, billing, upload handling beyond transport, or broadcast orchestration.
- Services own use cases and enforce policy regardless of whether the caller is the admin UI, advertiser portal, API, or bot.
- Repositories own persistence only. They should not make campaign policy decisions or send messages.
- Shared UI components (navigation, cards, forms, modals) are presentation-only and may consume view models; editorial and advertising components remain distinct feature areas.
- Define stable schemas/contracts and service tests before redesigning templates. Preserve existing URLs or add compatibility redirects.

## Existing editor/admin console inventory (from current branch)

The admin/editor console is mounted at `/admin` and protected by `require_editor`.

- **Story Moderation / Editorial:** `/admin` displays pending story clusters, source references, suggested timeline tags, approval action, broadcast preview, and recent approval log. The route builds the template context from in-memory `PENDING_CLUSTERS`, `SOURCES`, and `TIMELINE_TAGS`; approval invokes `process_approve_cluster`. The template itself labels the console “Phase 2 mock POST endpoints,” so persistence/workflow durability must be verified before treating it as a production newsroom CMS.
- **Ad Manager:** `/admin/ads` lists campaign status, impressions/quota, expiry, pricing tier, creative preview, renewal/top-up, pause/resume, broadcast to Telegram/Viber, and delete. Creation supports sponsor, campaign, category, destination URL, HTML text, active flag, impression quota and duration/date.
- **Provider Sources & Logos:** `/admin/sources` management for news/provider source details and logo uploads.
- **Obituaries / Janaza:** create/import notices, upload photo, toggle and delete.
- **Service Modules & Kill-Switch:** list modules, enable/disable and update suspension message.
- **Identity counts:** `/admin/api/identity-stats`, editor-protected aggregate view.
- **Public advertise/media-kit page:** `/advertise`, describes commercial formats and reach.

Keep the Editorial and Advertising modules separate in routes, services, templates, permissions, and tests. Shared shell/navigation is fine.

## Current ad engine findings / gaps

The current code has a basic sponsored-campaign model, not yet a complete self-serve advertiser platform.

- Repository: `data/repos/ads.py`. A campaign contains `campaign_name`, `sponsor_name`, `text_html`, `target_category`, `link_url`, `is_active`, `max_impressions`, `expires_at`, `pricing_tier`, and `impressions`.
- Selection: `get_active_sponsored_ad` selects one active campaign matching `all` or requested category, with quota and expiry checks, and balances by lowest impression count plus random tie-break.
- Impression accounting: `record_ad_impression` increments a counter. This is currently a simple counter; define exactly what qualifies as a billable impression and ensure updates are atomic under concurrent requests.
- Admin campaign management exists, but advertiser-owned login/tenant, ownership scoping, self-service campaign editing, moderation review, payment/order/invoice, audit history, and a campaign asset pipeline are not established by these paths.
- `routers/api_ads.py` currently exposes `GET /api/ads` and `POST /api/ads` without visible authentication/authorization. It also exposes a broadcast endpoint. These are critical security gaps: do not use these routes for public campaign management or allow untrusted callers to create/update campaigns or send broadcasts. Require explicit permission and move operations into services.
- Campaign creative is stored as `text_html` and rendered using Jinja `safe` in the admin preview. Arbitrary advertiser HTML is unsafe. Replace with constrained fields and escaped rendering; if rich text is necessary, sanitize with a strict allowlist server-side. Do not permit scripts, event attributes, iframe, arbitrary CSS, data URLs, or untrusted SVG.
- Existing engine appears oriented to text/HTML sponsor placements and Telegram/Viber sponsored broadcasts. Web display inventory, responsive image creatives, placements, campaign ownership, and reporting need explicit implementation rather than being assumed to exist.

## Ad engine requirements to implement

### Separate surfaces and placement inventory

Model inventory/placement explicitly. Suggested initial placement keys:
- `web_feed_card` (responsive in-feed sponsored card)
- `web_article_inline` (editorially separated inline placement)
- `web_sidebar` (desktop only; never force it onto narrow screens)
- `mobile_feed_card` (mobile web layout; not a separate native app)
- `telegram_broadcast` and `viber_broadcast` (distinct opt-in messaging inventory, separate from web ad impressions)

Each campaign/creative must specify permitted placement(s), target category/section, schedule, status, destination URL, and commercial limit. Do not count Telegram/Viber deliveries as web impressions. Clearly label paid placements as “Sponsored” / “އިޝްތިހާރު” as appropriate and preserve editorial independence.

### Advertiser self-service workflow

1. Advertiser creates an account or is invited; verify email/phone and business contact.
2. Advertiser can only access campaigns/assets owned by their advertiser organization.
3. Draft campaign → upload creative → preview web desktop and mobile → submit for editorial/ad-ops review.
4. Staff approve/reject with reason. Approval is required before serving; edits to a live creative return it to review.
5. Campaign owner can edit draft, pause/resume within policy, update schedule/destination/creative, see delivery stats, and request renewal. They cannot change price, quotas, payment status, approval state, or another advertiser's campaign.
6. Keep audit history for campaign and creative changes, approval decisions, status transitions, quota changes, billing adjustments, and broadcasts.
7. Campaign status is server-derived: draft, submitted, under_review, approved, scheduled, serving, paused, rejected, exhausted, expired, archived. An advertiser cannot self-approve.

### Creative and upload policy

Use server-side limits enforced before fully buffering files, plus reverse-proxy/request-body limits. Initial safe policy (configurable by admins):
- Accepted raster formats: JPEG, PNG, WebP. Reject SVG, GIF/animation, HTML, JS, PDF, executable/archive formats, and unknown types for ad creatives.
- Verify MIME by content sniffing and decode/re-encode the image. Do not trust filename or client MIME.
- Max file size: 500 KB per image; max 3 creative assets per campaign; max dimensions 2000 x 2000 pixels; max total pixels 4 megapixels after decode. Reject oversized dimensions and malformed files.
- Generate random asset IDs; store outside the web app's executable/static source tree or in object storage. Serve through a controlled asset route/CDN with correct content type, cache policy, and no directory listing.
- Store original metadata and generated rendition references. Create responsive variants (e.g. 320w, 640w, 1200w) and use `srcset`/appropriate aspect ratio. Do not upscale.
- Define format-specific ratios per placement, e.g. feed card 1:1 or 4:3, desktop banner 3:1, mobile banner 2:1. Avoid requiring one asset to stretch across desktop and mobile; allow dedicated responsive variants.
- Accessibility: advertiser supplies alt text; reject or flag missing alt text for image creatives.
- Text creative limits: headline 80 characters, body 160 characters, CTA label 24 characters; URL must be HTTPS except approved local development, reject unsafe schemes and private-network destinations. Validate redirects/destination policy.
- Do not allow auto-playing video, popups, intrusive interstitials, flashing creatives, or tracking pixels in the initial product.

### Ad selection, quota and reporting

- Eligibility is computed in a dedicated ad service using active/approved state, schedule, placement, section, quota, and payment status.
- Implement atomic quota reservation/increment with concurrency-safe database operations. Add idempotency/deduplication for impression events.
- Define reporting separately: served, viewable impression (if instrumented), click, CTR, delivery by placement/device/day, and billable event. Do not label a server response or bot send as a human view.
- Add advertiser-visible reports scoped to their organization; admin reporting can see all.
- Add budget/order/payment state and immutable pricing snapshot before commercial launch. Until then mark billing and impression numbers as non-billable estimates.
- Provide frequency caps, fallback house ads/no-ad response, and delivery pacing. Never let a single request block on broadcast sending.
- Broadcasts must be separately authorized, previewed, explicitly confirmed, rate-limited, and queued; record provider outcomes. Do not expose broadcast API publicly.

## Refactor and verification plan

1. Inventory all templates, routers, APIs, repository calls, editorial actions, and ad actions. Draw the dependency graph and identify any template/JS-to-business-rule coupling.
2. Extract editorial use cases and ad campaign use cases into `services/editorial_service.py` and `services/ad_campaign_service.py` (or established equivalent); move authorization/policy into services.
3. Keep repository methods persistence-only. Introduce typed request/response/view models.
4. Secure or remove public `/api/ads` management and broadcast routes. Add advertiser auth and organization ownership.
5. Build creative upload validation/storage/rendition pipeline with tests for size, MIME spoofing, extension spoofing, SVG, dimensions, malformed data, and safe output.
6. Add service tests for approval transitions, ownership, serving eligibility, quota races/idempotency, billing/report boundaries, and no delivery when unapproved/paused/expired/exhausted.
7. Add route tests for editor vs advertiser vs anonymous access. Add UI tests for desktop and mobile previews, accessible labels, and no raw untrusted HTML.
8. Run existing full suite and migrations against SQLite and Postgres staging. No production DB migration or deploy without explicit approval.

## Agent instructions

Treat this document as acceptance criteria. Do not claim separation, advertiser self-service, secure uploads, or monetization readiness until the code and tests demonstrate each requirement. Work in small commits. Preserve public news/bids/jobs browsing and existing Telegram/Viber bot behavior. Do not work on scraper architecture until the auth, UI/business separation, and ad access-control regressions are verified.
