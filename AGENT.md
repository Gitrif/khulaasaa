# AGENT GUIDELINES & ARCHITECTURE CONTRACT: KHULAASAA

## 1. File Size, Modularity & Code Organization Policy

### 1.1 Purpose
All code must remain readable, modular, maintainable, testable, and easy for another developer or AI coding agent to understand.
The objective is not to minimize line counts at any cost. The objective is to prevent oversized, tightly coupled files, duplicated business logic, unclear responsibilities, and unnecessary architectural complexity.
**The 500-line guideline is a maintainability warning, not an unconditional splitting rule.**
This policy applies to all production code, including Python modules, FastAPI routers, services, JavaScript, CSS, Jinja templates, models, schemas, background workers, and supporting modules.

### 1.2 File-Size Guidelines
| File size | Required action |
|---|---|
| Under 500 lines | Preferred. Maintain clear responsibility and cohesion. |
| 500–800 lines | Review the module for multiple responsibilities, duplicated logic, and opportunities for meaningful extraction. Document why it remains large if no beneficial refactoring is warranted. |
| Over 800 lines | Mandatory architectural review. Refactor where beneficial or document a specific technical justification for retaining the file. |

Count actual source lines consistently. Do not manipulate blank lines, comments, formatting, or file boundaries merely to meet the thresholds.

### 1.3 One Clear Responsibility per Module
- **Routers**: HTTP requests, parameter parsing, authentication and authorization enforcement, service orchestration, and response selection.
- **Services**: Business rules, application workflows, ingestion orchestration, and coordination between persistence and external systems.
- **Repositories/Data-Access Modules**: Reusable database access and query logic where separation provides a clear benefit.
- **Models and Schemas**: Domain data structures, persistence mappings, and validation contracts appropriate to their layer.
- **Presentation Helpers**: Reusable formatting, view-model construction, filter options, and template-ready data preparation.
- **Jinja Templates**: HTML rendering and minimal presentation conditionals. Do not execute SQL or heavy business transformations in templates.
- **Frontend JavaScript**: Browser interactions, UI state, and communication with existing server endpoints.
- **CSS**: Styling, layout, and responsive presentation.
- **Background Workers**: Scheduled or asynchronous execution, with clear ownership of task lifecycle and concurrency.

### 1.4 Split by Cohesion, Not by Line Count
When considering a refactor, ask:
1. Does this file contain multiple independent responsibilities?
2. Can a group of functions or classes be understood and tested independently?
3. Does extracting that group establish a clearer interface?
4. Will the extraction reduce coupling or make future changes safer?
5. Can the new module be reused without creating circular imports or hidden dependencies?
6. Will another developer be able to locate the relevant behavior more easily?

*Split the module when the answers indicate a meaningful architectural improvement. Keep related code together when separating it would make the system harder to understand.*

### 1.5 Prohibited Practices
- Do not split files into trivial modules solely to meet the 500-line guideline.
- Do not create one-function files without a meaningful architectural reason.
- Do not introduce excessive wrappers, forwarding functions, or redundant abstraction layers.
- Do not move business logic into helpers without clarifying ownership or reducing coupling.
- Do not create circular imports or dependency chains that are harder to follow than the original implementation.
- Do not duplicate business rules across routers, services, templates, JavaScript, or multiple service modules.
- Do not create competing implementations of the same feature.
- Do not rename, relocate, or reorganize unrelated files during a narrowly scoped task.
- Do not rewrite working functionality merely to satisfy a line-count target.
- Do not remove tests, comments, validation, authorization checks, or error handling to reduce file size.

**A refactor that reduces line count but increases complexity is not an acceptable refactor.**

### 1.6 One Source of Truth & Dependency Direction
Each business rule must have one authoritative implementation.
- Lower-level shared modules must not depend on high-level routers or templates.
- Presentation modules must not become the owners of business rules.
- Business services must not depend on browser-specific code.
- Shared modules must not become dumping grounds for unrelated functions.
- Authorization and security enforcement remain on the server, even when UI elements control button visibility.

### 1.7 Zero-Emoji Design Policy & Verification
Zero emojis in Telegram bot messages, menus, callbacks, alerts, and web templates. Use clean typography, badges, and SVG icons. Always run `python scripts/lint_cleaner.py` before finalizing changes.

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
