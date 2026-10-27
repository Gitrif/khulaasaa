# Khulaasaa — Verified Maldivian News, Procurement & Intelligence Portal

Khulaasaa (Dispatch) is a modular Python/FastAPI intelligence platform aggregating verified Maldivian news, national procurement tenders, public employment vacancies, and community notices into a single real-time portal.

---

## 1. System Architecture

```text
External Sources (Gazette, Media Outlets, SOE Portals, Telegram Channels)
    │
    ▼
Scraper Adapters (`scrapers/news/`, `scrapers/tenders/`, `scrapers/jobs.py`)
    │ (pure extraction, parsing, zero DB side effects)
    ▼
Domain Ingestion Services (`services/news_service.py`, `services/tenders_service.py`, `services/jobs_service.py`)
    │ (validation, normalization, clustering, classification)
    ▼
Canonical Repositories (`data/repos/`) & Alert Dispatcher (`alerts/`)
    │ (atomic upsert, deduplication)             │ (Telegram / Viber)
    ▼                                            ▼
Database (SQLite / PostgreSQL Supabase)    Subscribers / Channels
    │
    ▼
Read / Query Services (`query_articles`, `query_bids`, `query_jobs`)
    │
    ├──► Presentation Routers (`routers/web_ui.py`, `routers/web_bids.py`, `routers/web_jobs.py`)
    │         ▼
    │    Jinja2 UI Templates (`templates/`)
    │
    └──► API Endpoints (`routers/api_news.py`, `routers/api_jobs.py`, `routers/api_rfq.py`)
```

---

## 2. Ingestion Pipelines

### 📰 News Ingestion
- **Sources:** Haftha (WordPress REST), Atoll Times, Dhauru, Adhadhu, Sun, PSM, Standard (RSS), MV Crisis & Telegram channels, Mihaaru, and Miadhu.
- **Engine:** `scrapers/news/engine.py` concurrent dispatch.
- **Processing:** Raw intake partitions regular news from obituary announcements. Regular news is clustered across publishers using semantic keyword matching and published timestamps.
- **Persistence:** Individual publisher articles are stored idempotently in `articles`. Clustered feed views are cached in-memory with background stale-while-revalidate synchronization.
- **Alerts:** Breaking multi-source stories dispatch to configured Telegram subscribers and channels.

### 🏛️ Tenders & Procurement
- **Sources:** Maldives Government Gazette (`gazette.gov.mv/iulaan?type=beelan`) with multi-page pagination and duplicate-page cycle detection, plus SOE / Ministry procurement portals (Finance, Tourism, MWSC, STELCO, STO).
- **Processing:** Dhivehi titles and venues are normalized and translated to English. Submission deadlines and venues are parsed into structured ISO timestamps.
- **Persistence:** Upserted into `bids` canonical repository with duplicate suppression. Expired tenders are automatically purged after retention threshold.
- **Alerts:** Immediate notification to Telegram and Viber procurement subscribers based on industry disciplines and categories.

### 💼 Jobs & Careers
- **Sources:** Maldives Government Gazette vacancies (`gazette.gov.mv/iulaan?type=vazeefaa`) and National Careers Service (`mycareer.gov.mv/en/jobs`).
- **Processing:** Evaluated against Maldivian job market disciplines (Healthcare, IT, Finance/Procurement, Sea/Air/Land Transport, Engineering, Education, etc.). Standardized employer logos and application source hierarchies are attached.
- **Persistence:** Canonical `jobs` table with deduplicated notice identifiers.
- **UI & Empty States:** Live views display genuine persisted database records. When no live records match filters, an honest empty state is rendered (no synthetic demo fallback in production).

---

## 3. Getting Started

### Prerequisites
- Python 3.12+
- SQLite3 or PostgreSQL (Supabase)

### Setup & Run

```bash
# 1. Clone & activate virtual environment
python3 -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment configuration
cp .env.example .env

# 4. Start development server
uvicorn app:app --reload --port 8300
```

### Application URLs
- **Public News Feed:** `http://localhost:8300/`
- **Procurement & Bids:** `http://localhost:8300/bids`
- **Jobs & Vacancies:** `http://localhost:8300/jobs`
- **CV Builder:** `http://localhost:8300/jobs/cv`
- **Obituaries / Janaza:** `http://localhost:8300/obituaries`
- **Admin Console:** `http://localhost:8300/admin` (HTTP Basic: `editor` / set via `EDITOR_PASSWORD`)
- **Health Check:** `http://localhost:8300/healthz`

---

## 4. Operational Commands & Testing

```bash
# Run complete test suite (230+ unit & integration tests)
pytest

# Run code cleanliness & invariant checker (< 500 lines, zero-emoji policy)
python scripts/lint_cleaner.py

# Manually trigger scraper verification & database refresh
python scripts/reset_and_rescrape.py
```

---

## 5. Background Scheduler & Lifecycle

- Application startup initializes canonical schemas via `data/init_db.py`.
- Background tasks are coordinated in `main.py` via `lifespan`:
  - **News Sync:** Every 3 minutes.
  - **Procurement Sync:** Every 6 minutes.
  - **Jobs Sync:** Every 15 minutes.
  - **Telegram Bot Polling:** Real-time updates and interactive menu navigation.
- All background threads observe `_SHUTDOWN_EVENT` for immediate and clean shutdown during process termination.
