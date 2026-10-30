# Khulaasaa Auth, Cross-Channel Identity, and Page Performance Report

**Branch:** `fix/auth-registration-and-page-performance`  
**Status:** Draft PR; not merged or deployed.

## Scope

This change set addresses web registration/login safety, Telegram/Viber identity tracking, provider verification, and initial diagnostics for the reported slow page loads. Scraper refactoring remains out of scope.

## Identity model

- The existing `users` table remains the canonical Khulaasaa account registry.
- New `user_identities` records one stable provider identity per `(provider, provider_user_id)` for Telegram and Viber.
- A bot-only identity may have `user_id = NULL`; it is still recorded and can receive public bot information.
- A verified channel-linking flow maps an identity to an existing Khulaasaa account.
- One provider identity cannot silently transfer between accounts. Conflicting links fail and require recovery.
- `account_origin` distinguishes web-created accounts from Telegram Mini App-created accounts.
- Existing users and bot subscriber records are backfilled idempotently. Existing unverified IDs are not treated as verified account links.
- Admin-only aggregate counts are available at `GET /admin/api/identity-stats`. The response explicitly warns that unlinked Telegram and Viber identities cannot be reliably deduplicated across platforms.

## Authentication/security changes

- Registered the existing `routers.api_auth` router in the FastAPI application.
- Duplicate email registration returns HTTP 409 rather than issuing a session for the existing account; the write path also handles a concurrent duplicate-registration race.
- Telegram Mini App login validates Telegram's signed `initData` and freshness window. The browser sends the signed payload rather than trusting `initDataUnsafe` identifiers.
- Telegram Mini App-created accounts use random, non-routable internal email aliases. Registration rejects reserved `.invalid` and `.internal` domains to prevent synthetic-account collisions.
- Direct Viber-ID login is rejected. Viber identity must be proven by the user messaging the bot with the single-use PIN.
- The Viber verification API no longer trusts a Viber ID supplied by the browser.
- Viber webhook requests require a valid `X-Viber-Content-Signature` HMAC.
- Telegram webhook mode requires `TELEGRAM_WEBHOOK_SECRET`; without it, that endpoint fails closed. The current application startup still starts Telegram polling, so this secret is only needed if the deployment is intentionally switched to webhook mode.
- Subscriber-list, manual subscribe, and test-message endpoints are restricted to the editor credential.
- Gateway-managed local shadow accounts no longer use a fixed known password. A one-time migration rotates legacy hashes matching the historical fixed password.
- Transient Hooks85 session-verification failures are briefly cached to avoid repeating slow gateway timeouts for every page/API request. Explicit 401/403 invalid-session responses are not cached.

## UI work completed in this branch

- Corrected the sign-in form to send the backend's expected `email` field (the old UI sent `identifier`, which caused login failure).
- Changed the login field to an email input with browser autofill semantics; registration fields now have matching autocomplete hints.
- Replaced stale Telegram/Viber linking actions inside the global modal (which called endpoints that are no longer the supported verification flow) with accurate connection status and links to `/account/channels`.
- Replaced stale alert-preference controls inside the modal (which posted to an outdated API) with a link to the dedicated `/account/alerts` page.
- Clarified that public Telegram/Viber bot information remains accessible without a Khulaasaa web account; channel linking is only for connecting that provider identity to the account and personalizing alerts.
- Kept the avatar menu, connected-channel badges, and existing dedicated account pages.

## Page-load diagnostics

- Added a `Server-Timing: app;dur=...` response header.
- Server logs requests taking at least one second.
- Hooks85 session verification logs slow calls and temporarily caches transport/temporary server failures.
- Deferred Google Fonts loading to reduce render blocking while retaining Inter and Noto Sans Thaana.

These changes provide a way to determine whether slow pages are waiting on FastAPI/server-side work or browser-side resources. They do **not** prove the 15-second issue is fully resolved; that requires deployed response timings and a browser network waterfall. The latest workflow run is reported failed but the GitHub Actions API returned no job records, so there is no usable test log to diagnose from this integration. Do not treat the test suite as passing.

## Data safety and migration

- Schema additions are idempotent and cover both SQLite and the Supabase/PostgreSQL schema.
- Existing subscriber rows and verified account links are backfilled without deleting user or subscriber records.
- No production database was accessed or modified by this work.
- No deployment was performed.

## Tests added/updated

- Telegram Mini App signature validity, tampering, and stale payload checks.
- Identity upsert idempotency, owner-conflict rejection, and aggregate count behavior.
- Duplicate registration returns conflict and does not issue a second session.
- Transient Hooks85 verification failures are cached.
- Viber webhook signature validation and missing-signature rejection.
- Existing channel-link conflict test now expects safe failure rather than automatic transfer.
- Viber administration endpoint tests authenticate with editor credentials.

**Verification status:** Tests have been added/updated but have not been executed in this environment. The repository has no existing GitHub Actions workflow configured, and no local runtime/browser performance test has been run. Treat this as a draft requiring CI/test verification before merge.

## Required verification before merge

1. Run the targeted auth/identity/Viber tests, then the full existing pytest suite.
2. Verify registration, login, logout, password reset, session refresh, avatar menu, Telegram/Viber connection badges, story follows, and notifications in a browser.
3. Confirm the configured Viber token matches the bot's Viber Console token so signed webhook validation succeeds.
4. Measure `Server-Timing` for `/`, `/bids`, `/jobs`, `/rentals`, and `/obituaries`; inspect the browser network waterfall for external assets.
5. Review the admin-only identity counts and confirm existing linked users were backfilled correctly in a staging copy.
6. Only after approval, merge and deploy; then repeat the same checks against the live environment.
