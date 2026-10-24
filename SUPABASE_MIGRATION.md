# Supabase Cloud Database Migration & Deployment Guide

This guide details how to migrate Khulaasaa from local storage to **Supabase** (Cloud PostgreSQL) to prevent server disks from filling up with scraped data (articles, bids, jobs, and obituaries).

---

## 1. Why Supabase for Deployment?

- **Zero Local Disk Bloat**: All scraped tenders, news articles, and gazette notices stream directly into Supabase cloud storage rather than local SQLite/MySQL on the server.
- **Stateless Containers**: The application container (on Railway, Render, Fly.io, or VPS) can scale, restart, or redeploy without risking data loss.
- **Built-in Backups & Dashboard**: Supabase provides automatic daily backups, real-time metrics, a visual table editor, and SQL execution.
- **Connection Pooling**: Integrated Supavisor/PgBouncer pooler handles concurrent web requests and periodic scraping workers effortlessly.

---

## 2. Step-by-Step Setup

### Step 1: Create a Supabase Project
1. Log in to [supabase.com](https://supabase.com) and create a new project (e.g. `khulaasaa-prod`).
2. Choose a region closest to your users or server (e.g., Singapore `ap-southeast-1` or Frankfurt `eu-central-1`).
3. Save your database password securely.

### Step 2: Apply the PostgreSQL Schema
1. In the Supabase Dashboard, navigate to the **SQL Editor** on the left menu.
2. Open [`supabase/schema.sql`](supabase/schema.sql) from this repository, copy its contents, paste them into the SQL Editor, and click **Run**.
3. (Optional) Run [`supabase/seed.sql`](supabase/seed.sql) to populate the canonical Maldivian entity directory (SOEs, ministries, city councils).

### Step 3: Migrate Existing Scraped Data from Local SQLite
Run the automated migration script from your terminal:
```bash
python scripts/migrate_to_supabase.py --db-url "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"
```
The script will:
- Synchronize all canonical entities.
- Upsert all bids, active procurement notices, and milestones.
- Upsert all news articles and taxonomy tags.
- Transfer job postings, obituaries, sponsored ads, and subscribers.
- Reset PostgreSQL auto-increment sequences to prevent ID collisions.

### Step 4: Configure Deployment Environment Variables
In your deployment environment (e.g., Docker, Railway, Render, VPS `.env`), set:

```env
# Supabase PostgreSQL connection URI
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# (Optional) For high-concurrency pooler:
# DATABASE_URL=postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true

# (Optional) For Supabase Storage / Client SDK:
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_KEY=eyJhbGciOi...
```

---

## 3. How the Dual-Engine Architecture Works

| Environment | Behavior |
| :--- | :--- |
| **Local Dev & Testing (`pytest`)** | If `DATABASE_URL` is omitted, the app uses local SQLite (`data/khulaasaa.db` or temporary fixture databases). Tests run fast and 100% offline. |
| **Production Deployment** | When `DATABASE_URL` (or `SUPABASE_DB_URL`) is present, the app automatically switches to pooled Supabase PostgreSQL via `data.postgres_adapter`. |

---

## 4. Verification & Testing

Verify that both engines operate with full fidelity:
```bash
# Run the complete test suite
pytest
```
All existing tests pass with 0 regressions.
