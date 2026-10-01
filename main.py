"""
Phase 1 UI mockup server.

Serves the public feed, story timelines, and a mobile-first editor console
against in-memory mock data (data/mock_data.py). No database, no LLM, no
scrapers yet -- this locks the layout, routes, and journeys per the roadmap
before Phase 2 wires up real state and Phase 3 wires up the backend.

Run:
    uvicorn main:app --reload --port 8000

Admin console (HTTP Basic):
    user: editor   pass: set via EDITOR_PASSWORD env var (default "changeme")
"""
import os
import secrets
from typing import Optional

from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from data import mock_data as db

app = FastAPI(title="News Aggregator & Bias Tracker (UI mock)")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

security = HTTPBasic()
EDITOR_USER = os.environ.get("EDITOR_USERNAME", "editor")
EDITOR_PASS = os.environ.get("EDITOR_PASSWORD", "changeme")

if EDITOR_PASS == "changeme":
    import warnings
    warnings.warn(
        "EDITOR_PASSWORD is still the default 'changeme'. Fine for local "
        "dev, NOT fine for anything reachable outside your own machine -- "
        "set a real value via the environment (see .env.example) before "
        "deploying anywhere.",
        stacklevel=2,
    )


@app.get("/healthz")
def healthz():
    """Liveness/readiness probe for Docker/orchestrators. Deliberately has
    no dependencies to check yet (no real DB or external service wired in
    at this stage) -- just confirms the process is up and serving."""
    return {"status": "ok"}


def require_editor(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, EDITOR_USER)
    correct_pass = secrets.compare_digest(credentials.password, EDITOR_PASS)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid editor credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


SOURCE_KIND_COLOR = {"wire": "#B3432B", "official": "#C89B3C", "press": "#5B6572"}


def accent_color(evt: dict) -> str:
    """Left-border accent: tag color, else topic color, else first source's
    kind color, else neutral slate. Mirrors the static preview's logic so
    breaking/major/general cards read as one consistent visual language."""
    if evt.get("tag_objs"):
        return evt["tag_objs"][0]["color"]
    if evt.get("topic_obj"):
        return evt["topic_obj"]["color"]
    if evt.get("source_objs"):
        return SOURCE_KIND_COLOR.get(evt["source_objs"][0]["kind"], "#5B6572")
    return "#5B6572"


def enrich_event(evt: dict) -> dict:
    """Attach resolved source/tag/topic objects for template convenience."""
    source_objs = [db.SOURCES[s] for s in evt["sources"] if s in db.SOURCES]
    tag_objs = [db.TIMELINE_TAGS[t] for t in evt.get("tags", []) if t in db.TIMELINE_TAGS]
    topic_obj = db.TOPICS.get(evt.get("topic"))
    search_parts = [evt["headline"], evt.get("summary", "")]
    search_parts += [s["name"] for s in source_objs]
    search_parts += [t["label"] for t in tag_objs]
    if topic_obj:
        search_parts.append(topic_obj["label"])
    result = {
        **evt,
        "source_objs": source_objs,
        "tag_objs": tag_objs,
        "topic_obj": topic_obj,
        "search_blob": " ".join(search_parts).lower(),
    }
    result["accent"] = accent_color(result)
    return result


# ---------------------------------------------------------------- Public feed
@app.get("/", response_class=HTMLResponse)
def public_feed(request: Request, tag: Optional[str] = None, topic: Optional[str] = None):
    events = [enrich_event(e) for e in db.EVENTS]

    # Tag/topic filters apply across all three sections at once, so a filter
    # like "MMPRC Scandal" or "Tax & Revenue" narrows breaking+major+general
    # together rather than just the section that happens to hold it today.
    if tag:
        events = [e for e in events if tag in e.get("tags", [])]
    if topic:
        events = [e for e in events if e.get("topic") == topic]

    sections = {
        "breaking": [e for e in events if e["section"] == "breaking"],
        "major": [e for e in events if e["section"] == "major"],
        "general": [e for e in events if e["section"] == "general"],
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "sections": sections,
            "trending": db.TRENDING,
            "all_tags": list(db.TIMELINE_TAGS.values()),
            "all_topics": list(db.TOPICS.values()),
            "active_tag": tag,
            "active_topic": topic,
        },
    )


# ------------------------------------------------------------------ Timeline
@app.get("/timeline/{story_id}", response_class=HTMLResponse)
def timeline(request: Request, story_id: str):
    story = db.TIMELINES.get(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Timeline not found")

    milestones = []
    for m in story["milestones"]:
        milestones.append(
            {**m, "source_objs": [db.SOURCES[s] for s in m["sources"] if s in db.SOURCES]}
        )
    # sort newest first for display, oldest-first order preserved in data
    milestones_sorted = sorted(milestones, key=lambda m: m["date_iso"], reverse=True)

    return templates.TemplateResponse(
        "timeline.html",
        {
            "request": request,
            "story": story,
            "tag": db.TIMELINE_TAGS.get(story["tag"]),
            "milestones": milestones_sorted,
        },
    )


# --------------------------------------------------------------------- Bids
# Paywall stub: real auth/entitlements are Phase 2 work (see roadmap in
# README). For this mock, ?unlocked=1 simulates a paying, signed-in user
# so the sort/filter UI can actually be demonstrated end-to-end.
@app.get("/bids", response_class=HTMLResponse)
def bids(request: Request, agency: Optional[str] = None, discipline: Optional[str] = None,
          type: Optional[str] = None, unlocked: Optional[str] = None):
    rows = db.BIDS
    if agency:
        rows = [b for b in rows if b["agency"] == agency]
    if discipline:
        rows = [b for b in rows if b["discipline"] == discipline]
    if type:
        rows = [b for b in rows if b["gazette_type"] == type]

    return templates.TemplateResponse(
        "bids.html",
        {
            "request": request,
            "bids": rows,
            "is_unlocked": unlocked == "1",
            "agencies": sorted({b["agency"] for b in db.BIDS}),
            "disciplines": sorted({b["discipline"] for b in db.BIDS}),
            "types": sorted({b["gazette_type"] for b in db.BIDS}),
            "active_agency": agency,
            "active_discipline": discipline,
            "active_type": type,
        },
    )


# --------------------------------------------------------------------- Jobs
@app.get("/jobs", response_class=HTMLResponse)
def jobs(request: Request, discipline: Optional[str] = None):
    rows = db.JOBS
    if discipline:
        rows = [j for j in rows if j["discipline"] == discipline]
    return templates.TemplateResponse(
        "jobs.html",
        {
            "request": request,
            "jobs": rows,
            "disciplines": sorted({j["discipline"] for j in db.JOBS}),
            "active_discipline": discipline,
        },
    )


# --------------------------------------------------------------- Admin console
@app.get("/admin", response_class=HTMLResponse)
def admin_console(request: Request, editor: str = Depends(require_editor)):
    clusters = []
    for c in db.PENDING_CLUSTERS:
        clusters.append(
            {
                **c,
                "source_objs": [db.SOURCES[s] for s in c["sources"] if s in db.SOURCES],
                "tag_objs": [db.TIMELINE_TAGS[t] for t in c["suggested_tags"] if t in db.TIMELINE_TAGS],
            }
        )
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "editor": editor,
            "clusters": clusters,
            "all_tags": list(db.TIMELINE_TAGS.values()),
            "approval_log": list(reversed(db.APPROVAL_LOG)),
        },
    )


@app.post("/admin/approve/{cluster_id}")
def approve_cluster(
    cluster_id: str,
    request: Request,
    tags: list[str] = Form(default=[]),
    editor: str = Depends(require_editor),
):
    match = next((c for c in db.PENDING_CLUSTERS if c["id"] == cluster_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Cluster not found or already approved")
    db.approve_cluster(cluster_id, tags)
    # Mock validation of "no page stuttering": redirect back, 303 avoids
    # a resubmission-on-refresh prompt.
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


# --------------------------------------------------------- Broadcast preview
@app.get("/admin/broadcast-preview/{cluster_id}", response_class=HTMLResponse)
def broadcast_preview(request: Request, cluster_id: str, editor: str = Depends(require_editor)):
    cluster = next((c for c in db.PENDING_CLUSTERS if c["id"] == cluster_id), None)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    cluster = {
        **cluster,
        "tag_objs": [db.TIMELINE_TAGS[t] for t in cluster["suggested_tags"] if t in db.TIMELINE_TAGS],
    }
    return templates.TemplateResponse(
        "broadcast_preview.html",
        {"request": request, "cluster": cluster},
    )
