# AGENT GUIDELINES & ARCHITECTURE CONTRACT: KHULAASAA

## 1. Strict Codebase Invariants
- **Line Count Cap (< 500 Lines)**: Every Python (`.py`) and JavaScript (`.js`) file must strictly stay below 500 lines. Break modules by domain/responsibility (e.g., formatters, clients, dispatchers, keyboards).
- **Clean Architecture & Separation of Concerns**:
  - **Presentation Layer (UI)**: Jinja2 templates in `templates/` and client JS/CSS in `static/`. Templates must not execute business logic or raw SQL.
  - **Routing Layer**: FastAPI APIRouters in `routers/` handle HTTP requests, input validation, and HTTP exceptions.
  - **Business Logic / Services**: `scrapers/`, `alerts/`, and `services/` contain pure business rules, web scraping, formatters, and dispatch logic.
  - **Data Access Layer**: `data/database.py` (facade) and `data/repos/` contain pure SQL/repository operations.
- **Zero-Emoji Design Policy**: Zero emojis in Telegram bot messages, menus, callbacks, and web templates. Use clean typography, badges, and SVG icons.
- **Lint & Clean Verification**: Always run `python scripts/lint_cleaner.py` before finalizing changes.

---

## 2. Multi-Component Domain Architecture
Khulaasaa is partitioned into 4 focused frontends sharing a unified backend, database, and auth layer:

| Domain | Focus | Key Actions |
|---|---|---|
| **`news.khulaasaa.com`** | Editorial News Aggregator | Breaking alerts, news timelines, cross-source comparison. |
| **`bids.khulaasaa.com`** | Procurement & Tenders | Gazette & SOE bids, deadline tracking, link to hooks85 ERP. |
| **`jobs.khulaasaa.com`** | National Careers & Vacancies | Gazette & SOE openings, salary transparency, link to CV tool. |
| **`utilities.khulaasaa.com`** | Micro-SaaS Business Tools | CV Creator, Company Profile Maker, ID / Bill Parser. |

### Contextual Bridge Linking
- `bids.khulaasaa.com` -> Tender cards feature **Prepare Bid Package &rarr;** routing directly to hooks85 ERP.
- `jobs.khulaasaa.com` -> Job cards feature **Prepare CV for this job &rarr;** routing to `utilities.khulaasaa.com/cv`.

---

## 3. hooks85 Integration & Auth / Subscription Gateway
- **Single Sign-On (SSO) & Essentials-v1 Contract**:
  - Implemented in `services/hooks85_service.py` adhering to `essentials/v1`.
  - Registered App Slug: `app_khulaasaa` via `PUT {HOOKS85_GATEWAY_URL}/internal/v1/apps/app_khulaasaa/manifest`.
  - Primary Auth: `POST {HOOKS85_GATEWAY_URL}/api/v1/auth/password/login` and `POST {HOOKS85_GATEWAY_URL}/api/v1/auth/register`.
  - Session Verification: `GET {HOOKS85_GATEWAY_URL}/api/v1/auth/session` via `hooks85_session` cookie (cached 30s per essentials-v1 contract).
  - Dual-mode fallback: Falls back to local SQLite credentials if Gateway is offline.
- **Subscription & RBAC Management**:
  - Validates subscription status (`billing.status in ("active", "trial")` or `billing.can_write == true`) directly from hooks85 Gateway session.
  - Payment Gateway at `{HOOKS85_PAYMENT_URL}/api/v1/plans` manages tier entitlements.
  - Paid plans (Pro Feed, Follow Quotas, Unlimited Document Exports) are provisioned through hooks85 Admin Console.
- **Borrowed ERP Modules**:
  - Invoicing, Quotation, Letter Generator, Company Profile, and BOQ Maker are maintained as hooks85 core engines and surfaced contextually in Khulaasaa.
  - Free tier documents generated in Khulaasaa contain a subtle footer watermark:  
    `Generated with Khulaasaa Utilities • khulaasaa.com • Upgrade to remove watermark`

---

## 4. Language & Formatting Standards
- **English First**: Default presentation is English. Transliterated / translated titles are prioritized. Thaana is used solely when no English translation is available.
- **Date Normalization**:
  - Submission deadlines are parsed to ISO in scrapers and rendered via `| format_tender_date` as `04 Nov 2026, 11:00 AM`.
  - Dhivehi calendar dates/months (e.g. `އޮކްޓޯބަރ` -> `Oct`) are normalized to English via `| normalize_tender_info`.
- **Source Button Consistency**:
  - All source links across News, Bids, and Jobs use `.source-action-btn` with generous padding, source icon, and `Label &rarr;`.

---

## 5. Ad Engine & Monetization
- **Native Card Styling**: Ads use `<article class="story-card ad-card ...">` with 100% width, identical padding (`p-4 sm:p-5`), hairline border, and shadow.
- **Quotas & Expiry**: Managed in `data/repos/ads_repo.py` supporting view/impression quotas (e.g. 1,000 views) and time-based cutoffs (e.g. 30 days).
- **Future Ad Network (AdSense/AdMob for Maldives)**: CPC and CPV tracking hooks ready for external publisher embeds.
