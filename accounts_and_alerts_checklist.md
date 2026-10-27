# User Accounts, Following, Preferences & Notification Workflow
## Implementation Checklist & Phased Roadmap

**Repository:** `https://github.com/Gitrif/khulaasaa`  
**Target Branch:** `main`  
**Current Baseline Commit:** `3ade188`  
**Status:** Complete & Fully Verified (Phases 1, 2, and 3 All Passing - 254 Tests)

---

## 1. Architectural Invariants: What We Are NOT Doing

- **NO rewriting the application:** We preserve existing FastAPI routers, Jinja2 templates, repository patterns, and background workers.
- **NO parallel alert pipelines:** Alerts must originate strictly from database state changes (new/updated records), never directly from scraper loops.
- **NO hardcoded or client-trusted identities:** Telegram chat IDs and Viber IDs must be verified through server-generated linking tokens, not client write-in inputs.
- **NO noisy unsolicited broadcasts:** Follows define *what* content is relevant; preferences define *where and when* notifications are sent. Connecting a channel does not subscribe a user to unsolicited categories.
- **NO destructive migrations:** Preserves existing database schemas for SQLite and Supabase PostgreSQL.

---

## 2. Implementation Checklist by Phase

### Phase 1: Accounts & Following Model (COMPLETED)
- [x] **1.1 Canonical Database Schema Updates (`data/schema.py` & `supabase/schema.sql`):**
  - Add `user_follows` table:
    - `id` (PK, auto-increment)
    - `user_id` (FK -> `users(id)` ON DELETE CASCADE)
    - `target_type` (`story`, `topic`, `section`, `source`)
    - `target_id` (string slug / identifier)
    - `target_title` (display label)
    - `created_at` (timestamp)
    - Unique constraint: `UNIQUE(user_id, target_type, target_id)`
  - Add password recovery fields to `users`:
    - `reset_token_hash` (text), `reset_token_expires` (timestamp).
- [x] **1.2 Follows Repository (`data/repos/follows.py`):**
  - `add_follow(conn, user_id, target_type, target_id, target_title)`: Idempotent add with validation.
  - `remove_follow(conn, user_id, target_type, target_id)`: Idempotent remove.
  - `list_user_follows(conn, user_id, target_type=None)`: Retrieve user subscriptions.
  - `is_following(conn, user_id, target_type, target_id)`: Fast boolean check.
  - `get_followers_for_target(conn, target_type, target_id)`: Find all users following a given topic/story/source/section.
  - `get_user_follow_counts(conn, user_id)`: Breakdown counts.
- [x] **1.3 Authentication & Account Enhancement (`data/repos/users.py`, `routers/api_auth.py`):**
  - Password reset request (`POST /api/auth/forgot-password`) with non-enumerating response & SHA-256 hash storage.
  - Verification & consumption (`POST /api/auth/reset-password`) with single-use enforcement and session invalidation.
  - Session revocation and secure logout.
  - Current account details endpoint (`GET /api/account/me`, `PATCH /api/account/profile`, `POST /api/account/change-password`).
- [x] **1.4 Follows API Endpoints (`routers/api_follows.py`):**
  - `POST /api/follows`: Authenticated endpoint to follow a target.
  - `DELETE /api/follows`: Authenticated endpoint to unfollow a target.
  - `GET /api/follows`: List current user's follows.
  - `GET /api/follows/check`: Query follow status for UI badges.
- [x] **1.5 UI Templates & Navigation:**
  - Create `/following` dashboard (`templates/following.html`): View and manage followed stories, topics, sections, and publishers.
  - Create `/account` profile page (`templates/account.html`).
  - Update Header Avatar dropdown in `templates/base.html` with 5 exact links:
    1. My Account (`/account`)
    2. Following (`/following`)
    3. Alerts & Notifications (`/account/alerts`)
    4. Connected Channels (`/account/channels`)
    5. Sign Out
  - Contextual Follow/Unfollow buttons on story cards, topic chips, and story detail.
  - Guest authentication interceptor: Clicking follow while unauthenticated prompts login/registration modal and seamlessly resumes the action.

---

### Phase 2: Preferences & Truthful Channel Linking (COMPLETED)
- [x] **2.1 Preference & Channel Linking Schema (`data/schema.py` & `supabase/schema.sql`):**
  - Add `user_notification_preferences` table:
    - `user_id` (PK, FK -> `users(id)`)
    - `breaking_alerts` (INTEGER 1/0, default 1)
    - `followed_content_alerts` (INTEGER 1/0, default 1)
    - `telegram_enabled` (INTEGER 1/0, default 1)
    - `viber_enabled` (INTEGER 1/0, default 1)
    - `frequency` (`instant`, `digest`, default `instant`)
    - `quiet_hours_enabled` (INTEGER 1/0, default 0)
    - `quiet_hours_start` (text e.g. `'23:00'`)
    - `quiet_hours_end` (text e.g. `'07:00'`)
    - `timezone` (text, default `'Indian/Maldives'`)
    - `is_paused` (INTEGER 1/0, default 0)
  - Add `channel_link_tokens` table:
    - `token` (PK text, secure random token / PIN)
    - `user_id` (FK -> `users(id)`)
    - `channel` (`telegram`, `viber`)
    - `expires_at` (timestamp, 15m TTL)
  - Add `telegram_verified` and `viber_verified` integer flags to `users` table with backward-compatible migrations in `data/init_db.py`.
- [x] **2.2 Channel Linking Engine (`services/channel_linking_service.py`):**
  - Generate secure 15-minute expiring deep-linking tokens for Telegram (`https://t.me/<bot>?start=link_<token>`) and 6-digit numeric PINs for Viber.
  - In `alerts/telegram_bot.py`: On `/start link_<token>` or `/link <token>`, verify token, bind `user.telegram_chat_id = chat_id`, set `telegram_verified = 1`, consume token immediately, and send clean non-emoji confirmation.
  - In `alerts/viber.py`: Handle `link <PIN>` and `context` token verification with provider limitations handling.
  - Reassignment handling: Re-verifying a chat/user ID unlinks conflicting prior accounts securely.
  - Server-side disconnection endpoints (`POST /api/channels/telegram/disconnect`, `POST /api/channels/viber/disconnect`).
- [x] **2.3 Preference Endpoints & UI:**
  - `GET /api/account/preferences` & `PUT /api/account/preferences`.
  - Create `/account/alerts` page (`templates/account_alerts.html`): Explicit toggle controls for breaking news, followed content, quiet hours, instant/digest, and global pause/resume, strictly separating preference from channel connection status.
  - Create `/account/channels` page (`templates/account_channels.html`): Truthful verification indicators, 1-click deep-link connect for Telegram, 6-digit PIN connect for Viber, test alert triggers, and disconnect actions.
- [x] **2.4 Phase 2 Test Suite (`tests/test_preferences_and_channel_linking.py`):**
  - 8 comprehensive tests covering preference CRUD, validation, token expiration, single-use replay prevention, ownership transfer, channel disconnect, bot webhook handlers, and web views.
  - Full regression suite: 246 passed out of 246 tests.

---

### Phase 3: Delivery Reliability & Alert Decision Engine (COMPLETED)
- [x] **3.1 Logical Alert & Delivery Tracking Schema (`data/schema.py` & `supabase/schema.sql`):**
  - Add `notifications` table:
    - `id` (PK), `user_id` (FK), `event_key` (canonical versioned unique key), `content_type` (`news`, `tender`, `job`, `obituary`), `content_id` (text), `event_version` (int), `reason`, `reason_target`, `title`, `summary`, `url`, `is_urgent`, `frequency`, `is_read`, `created_at`.
    - DB constraint: `UNIQUE(user_id, event_key)`.
  - Add `notification_deliveries` table:
    - `id` (PK), `notification_id` (FK), `user_id` (FK), `channel` (`telegram`, `viber`), `destination`, `status` (`pending`, `delivered`, `failed`, `dead_letter`, `queued_quiet_hours`, `queued_digest`), `attempt_count`, `max_attempts`, `error_message`, `last_attempt_at`, `delivered_at`, timestamps.
    - DB constraint: `UNIQUE(notification_id, channel)`.
- [x] **3.2 Notification Repositories (`data/repos/notifications.py`):**
  - Idempotent `create_logical_notification`, `create_notification_delivery`, `update_delivery_status` with sanitized error redaction, `list_user_notifications`, `mark_notification_read`, `mark_all_notifications_read`, `get_unread_notification_count`.
- [x] **3.3 Alert Decision Service (`services/alert_decision_service.py`):**
  - Triggered strictly AFTER content persistence in domain services (never inside scrapers).
  - Evaluates breaking news and all 4 follow targets (`story`, `topic`, `section`, `source`).
  - Evaluates user preferences:
    - Global notification pause strictly respected (`is_paused == 1` skips all notifications).
    - Channel eligibility requires both verification (`telegram_verified == 1` / `viber_verified == 1`) AND active preference.
    - Quiet hours with Maldives timezone (UTC+5) evaluation: urgent breaking news bypasses quiet hours; routine follows are queued (`queued_quiet_hours`).
    - Digest frequency respected (`queued_digest`).
  - Creates 1 logical notification record per user and content event.
- [x] **3.4 Delivery Reliability Engine (`services/alert_delivery_service.py`):**
  - Independent channel dispatch: Telegram failure does not block Viber, and vice versa.
  - Sanitized logging: tokens, PINs, and secrets are strictly redacted.
  - Bounded retries: max 3 attempts before marking `dead_letter`.
- [x] **3.5 User Notification API (`routers/api_user_alerts.py`):**
  - `GET /api/account/notifications`, `POST /api/account/notifications/{id}/read`, `POST /api/account/notifications/read-all`.
- [x] **3.6 Comprehensive Test Suite (`tests/test_alert_engine_and_reliability.py`):**
  - 8 comprehensive tests covering event key versioning, timezone quiet hours, DB uniqueness, 4 follow targets, breaking vs quiet hours, global pause & unverified channels, independent channel deliveries & retries, and cross-user API isolation.
  - Full regression suite: 254 passed out of 254 tests with 0 warnings.
