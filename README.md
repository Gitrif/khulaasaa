# Dispatch — Phase 1 UI mock

Server-rendered FastAPI + Jinja2 + Tailwind (CDN). No database, LLM, or
scrapers yet — this is the Phase 1 deliverable from the roadmap: lock the
layout, routes, and editor journey before Phase 2/3 backend work starts.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8300
```

- Public feed: http://localhost:8300/
- Timeline: http://localhost:8300/timeline/mmprc-followup-2026
- Admin console: http://localhost:8300/admin
  - user `editor`, pass `changeme` (override via `EDITOR_USERNAME` /
    `EDITOR_PASSWORD` env vars — do this before anything but local demo use)
- Broadcast preview: reachable from a card's "Preview broadcast" button

## What's demonstrated

- **Public feed** (`/`) — Ground News–style cards: unified headline,
  2-sentence summary, horizontal source badges, tag filter nav.
- **Timeline** (`/timeline/{story_id}`) — vertical milestone rail, Dhivehi
  raw date strings displayed as-is (`date_raw`) alongside a normalized
  `date_iso` used for sorting — this is the seam Phase 3's date-normalization
  regex work will fill in for real scraped data. Milestones expand via
  native `<details>`, no JS framework.
- **Many-to-many schema mock** (`data/mock_data.py`) — `evt-1040` appears
  under both `mmprc` and `adeeb` tags simultaneously, standing in for the
  `article_timelines` junction table.
- **Admin console** (`/admin`) — mobile-first stacked cards, 44px+ tap
  targets, pre-checked tag chips (simulating LLM-suggested tags), fixed
  bottom bar. HTTPBasic-gated.
- **Approve action** (`POST /admin/approve/{cluster_id}`) — mutates the
  in-memory `PENDING_CLUSTERS` list and redirects with 303 (no
  resubmit-on-refresh, no full reload stutter).
- **Broadcast preview** — Telegram and Viber rendering mockups shown side
  by side from the same cluster data.

## Ad placements (IAB standard units)

Slots are marked as dashed placeholders in the UI, sized to real IAB units
so they drop into real inventory later without a layout rework:

| Slot | Size | Where | Why there |
|---|---|---|---|
| Leaderboard | 728×90 | Top of main content, above the fold, below the tag nav | Highest-viewability slot on the page; standard first placement on nearly every major news site |
| In-feed native | full-width card | Inside the major-stories grid, after the tracked narrative cards | Reads as part of the story rhythm rather than an interruption; performs best embedded in a list a reader is already scanning |
| In-content rectangle | 300×100 | Mid-way through the General news list | Breaks up the highest-volume, lowest-visual-weight section without interrupting a single story |
| Medium rectangle | 300×250 | Sidebar, under "Most read" | Classic desktop sidebar slot; only renders on ≥860px, so it never eats mobile screen space |

Left out for now, worth deciding on before Phase 4: a sticky mobile
anchor banner (320×50) at the screen bottom, and whether MIRA/Gazette
"official" content should ever sit directly adjacent to an ad (some
publishers keep a no-ad buffer around primary-source/official content
for trust reasons — your call).

## Layout notes (newsier pass)

- **Live ticker** at the very top — auto-scrolling, red, pulsing dot —
  carries only `breaking` items. This is the "something is happening right
  now" signal most general-interest readers scan for first.
- **One hero story**, not four equal-weight cards — the top major-narrative
  item gets outsized treatment (BBC/Reuters pattern), the rest sit in a
  denser 2-up grid beneath it.
- **"Most read" sidebar** — static mock ranking for now; real ranking
  would come from view counts once analytics exist. This is a cheap,
  high-payoff urgency/social-proof signal on real news sites.
- **Relative timestamps** ("2h ago", "1d ago") alongside the raw Dhivehi
  date on major stories — Phase 3's date-normalization work should emit
  both, since raw + relative serves different reading contexts (skimming
  vs. archival).
- Desktop grid collapses to a single column below 860px; nothing here
  depends on JS for layout, only the ticker animation and tab switching
  in the static preview file (the real app doesn't need the tab switcher
  at all — that's a preview-only convenience).


See `static/css/style.css` — ink/paper/lagoon/flag/gold palette, Spectral
(serif headlines) + Inter (UI), flat bordered cards with a tag-colored left
accent bar rather than rounded shadow cards.

## Running with Docker

Written for local testing before real deployment. **Not yet built or run**
from the environment this was written in (no Docker available there) — the
app logic itself is tested (see the route checks throughout this project's
development), but the container build itself needs confirming on your
machine.

```bash
cp .env.example .env
# edit .env -- at minimum, change EDITOR_PASSWORD away from "changeme"

docker compose up --build
```

(`docker compose up --build` will also work even if you skip the `cp` step
— `env_file` is marked optional in `docker-compose.yml` — but you'll get
the changeme warning in the logs and should still set a real password
before this is reachable by anyone else.)

**Do not scale this past one replica or add `--workers` to uvicorn yet.**
Confirmed by reading the code: `data/mock_data.py`'s admin-approval state
(`PENDING_CLUSTERS`, `APPROVAL_LOG`) is plain in-process Python state, not
a database. Multiple workers/replicas means multiple independent copies —
an approval done on one is invisible to requests landing on another. Both
`Dockerfile` and `docker-compose.yml` have comments on this; fix it by
wiring in a real datastore before scaling, not by working around it.

Then:
- http://localhost:8300 — news feed
- http://localhost:8300/bids, /jobs — the new pages
- http://localhost:8300/admin — editor console (credentials from `.env`)
- http://localhost:8300/healthz — liveness check, returns `{"status": "ok"}`

If the build fails, the most likely culprits given what's in this project:
`beautifulsoup4`/`requests` version pins in `requirements.txt` (added this
session, never installed inside a container before now), or a path issue
with the `static/`/`templates/` directories not copying correctly — check
`docker build` output for which `COPY` step fails, that narrows it fast.

**What Docker packaging does NOT do here**: it doesn't make the scrapers
live. `main.py` still only serves `data/mock_data.py` — containerizing the
app doesn't change what data it has access to. Wiring `scrapers/gazette.py`
and `scrapers/haftha.py` into a running pipeline (with real network access,
which the container will have, unlike this sandbox) is still a separate
piece of work from "the app runs in Docker."



- No real auth session/cookie — HTTPBasic re-prompts per browser session.
- No CSRF token on the approve form (add before this touches a real network).
- Tag list is hardcoded in `mock_data.py` — see open question below.
- No pagination on the public feed.

## Open questions for the contract (from the original brief)

1. **Editorial tag lists** (MMPRC Scandal, Thilamalé Bridge Project, etc.) —
   should these stay strictly pre-defined by editors, or should the local
   LLM be allowed to *propose* new macro-timelines when it detects a
   recurring pattern? Recommendation: LLM-suggested-but-editor-approved —
   mirror the same approve/reject pattern already built for clusters here,
   rather than either hardcoding forever or letting the model create
   canonical timelines unsupervised. That keeps one review surface instead
   of two.
2. **Server specs** (RAM / CPU / GPU) for the Docker host — needed before
   Phase 3 to pick an Ollama model size that fits comfortably (a 7–8B
   Dhivehi-capable model needs meaningfully different headroom than a 3B
   one), and to size Qdrant/pgvector memory. Please confirm before that
   phase's contract is finalized.
