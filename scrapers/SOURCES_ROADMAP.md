# Bids/tenders source roadmap

Build order, and why. Gazette.gov.mv ships first and alone — everything
below is queued, not started, until explicitly picked up.

## Tier 0 — building now
**gazette.gov.mv** (`scrapers/gazette.py`)
Confirmed primary discovery source. Real evidence this session: every SOE
and ministry tender sampled (HDC, Ministry of Finance/Beelan-backed) had a
matching gazette notice, even when the agency also runs its own listing.
Treat as the source of truth for "does this bid exist."

## Tier 1 — next, once Tier 0 is stable
**Major SOE sites, as enrichment (not discovery)**
Not a second place to *find* bids — a place to follow a gazette notice's
own link to get the actual documents (BOQ, drawings, full tender pack) that
gazette notices often only reference rather than host. Confirmed pattern:
HDC notices link to `hdc.com.mv/announcements/bids/`.

Add in this order (rough order of tender volume/value, not confirmed —
worth checking each agency's own gazette-notice count before committing):
1. **Housing Development Corporation** (hdc.com.mv) — confirmed link pattern this session
2. **STO** (State Trading Organization) — named in earlier gazette samples, not yet checked directly
3. **Fenaka Corporation** — island utilities, likely high tender volume, not yet checked
4. **MWSC** (Male' Water & Sewerage Company) — not yet checked
5. **Island Aviation Services**, **Maldive Gas Pvt Ltd** — both confirmed as real gazette-publishing agencies this session, not yet checked for their own site

For each: confirm (a) they run a public bids/tenders page at all, (b) whether
it's just a document repository (low scraping value beyond linking out) or
carries structured data gazette doesn't (higher value — build a scraper).

## Tier 2 — long tail, add selectively rather than all at once
**Island & atoll council websites**
~188 island councils + 20 atoll councils + city councils. Real risk: most
publish small-value local tenders (a single island's harbour repair, say)
that may or may not reliably reach gazette.gov.mv — unconfirmed either way,
not sampled this session. Recommendation: don't build 200 scrapers. Instead:
1. Spot-check 5-10 council sites against gazette.gov.mv coverage first —
   if their tenders already show up on gazette reliably, Tier 2 may not be
   needed at all beyond gazette's own Office/Agency filter (which already
   includes council secretariats, confirmed this session).
2. Only build dedicated council scrapers if that spot-check finds real gaps.

## Tier 3 — monitor, don't build against yet
**A future unified e-GP portal**
A government procurement-modernization report (found this session, not
previously known) describes the Beelan Portal as a stopgap the government
has stopped extending, in favor of a planned unified e-Government
Procurement platform — Phase I explicitly includes "publish tender notices
and awards online." Not live yet as far as this research found. Worth a
periodic check (quarterly?) rather than deep investment in gazette-specific
tooling that assumes permanence. If/when it launches, it may ship with an
actual API, which would be strictly better than scraping anything above.

## Dedup, built ahead of Tier 1
`scrapers/dedupe.py` — merges SourceRecords into one MergedBid, keyed on
normalized reference number (primary) or agency+title+date-proximity
(fallback, for the minority of notices without a parseable reference
number). Tested against a realistic two-source scenario modeled on real
HDC/gazette data — see the test run in this session's output. This exists
now, before Tier 1 starts, on purpose: adding a second source without a
merge layer already in place means shipping visible duplicates first and
fixing it later.
