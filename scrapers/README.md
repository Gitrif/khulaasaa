# haftha.mv scraper — status

**Confirmed by live inspection (2026-09-30):** real WordPress site, 6 categories
with confirmed URL slugs, article URLs as `haftha.mv/{id}/`, structured fields
per article (Thaana H1, romanized `og:title`, ISO `og:updated_time`, author
byline, categories, tags, thumbnail).

**Tested in this repo (`scrapers/haftha.py`):** Dhivehi-month byline date
parsing, category URL construction, article-ID extraction — all run against
real strings pulled from the live site, not invented examples.

**Not yet verified — do this before running at any real frequency:**
1. Read `haftha.mv/robots.txt`, `haftha.mv/editorial-policy`, and
   `haftha.mv/code-of-ethics` from a machine with normal internet access.
2. Check whether `haftha.mv/wp-json/wp/v2/posts` (WordPress REST API) is
   enabled — if so, use it instead of the HTML selectors below; it'd return
   clean JSON with zero selector-guessing.
3. Confirm the CSS selectors in `fetch_listing`/`fetch_article` against a real
   page load (browser devtools or `curl`) — the fetch tool used to inspect the
   site this session returns cleaned text, not raw HTML, so selectors are
   informed guesses based on standard WordPress/Elementor markup, not
   confirmed class names.

**Scope, deliberately:** this scraper captures metadata (title, date, author,
category, tags, thumbnail, canonical URL) for aggregation — not full article
bodies. See the copyright note at the bottom of `haftha.py`.

# gazette.gov.mv scraper — status

**Confirmed by live inspection (2026-09-30):** real domain is `gazette.gov.mv`
(not the bare `gazette.mv`). Notice URL pattern `iulaan/{id}` (+ a cleaner
`iulaan/print/{id}` view). Every notice has Type, Number, Published Date/Time,
Deadline, Agency, Title, Body. The listing page's own filter form already
supports Type and Office/Agency — agency filtering doesn't need to be built,
it's native.

**Tested in this repo (`scrapers/gazette.py`):** date/deadline parsing and a
first-pass discipline classifier — both run against real notices and real
titles pulled from the live site.

**Real finding from that test:** keyword classification against 6 real bid
titles caught the one construction tender correctly but put 5 of 6 into
"Other" — because most real gazette bids are land/resort/guesthouse **lease**
tenders, not construction/IT/medical procurement. Worth adding a "Real Estate
& Leasing" (or similar) discipline bucket before this ships, or the "Other"
bucket will dominate. This is exactly the kind of category-boundary problem
the Phase 3 LLM classifier should handle better than keyword matching.

**Not yet verified** — same three items as haftha.mv (robots.txt/ToS, a
possible JSON API, and confirmed HTML selectors from raw markup), plus:
1. The full Type-filter URL slug list (only one example slug seen:
   `?type=aanmu-mauloomaathu` for Public Info — the Bid slug itself wasn't
   captured).
2. The full Office/Agency dropdown values — it's a long `<select>`, and the
   fetch tool used this session doesn't return raw `<option value="">`
   attributes.
3. Whether `type=Beelan` is applied consistently to every real tender — one
   construction bid (V.Fulidhoo Police Post) didn't show a "Beelan" header in
   its search snippet, which is inconclusive but consistent with the earlier
   concern: don't rely on `type=Bid` alone, also catch `Work`/`Goods` types
   and title patterns like "Invitation for Bids" / "IFB".

# "All bids" — single source or many? (real finding)

Checked this directly: does gazette.gov.mv actually cover every publishing
agency, or do SOEs/ministries run separate tender pages gazette misses?

**Finding: gazette.gov.mv is already the de facto central hub.** Every HDC
tender found (2017–2021 sample) had a matching gazette.gov.mv notice, even
though HDC also lists the same tenders on its own site (hdc.com.mv). Same
pattern for Ministry of Finance-run tenders that require Beelan Portal
submission — the portal is where bidders *submit* documents, but the public
notice itself is still published via the gazette.

**Practical conclusion:** gazette.gov.mv doesn't need to be supplemented with
separate scrapers per agency for *discovery* — treat it as the single source
of truth for "does this bid exist." Agency sites (hdc.com.mv/announcements,
etc.) matter as a **per-notice enrichment step** — following the link a
gazette notice gives for the actual bid documents/BOQ — not as an independent
discovery source. This isn't a 100%-verified claim (sampled ~15 real notices,
not exhaustive), so the Phase 3 self-healing ingestion loop should still spot-
check a known agency's own tender page against what gazette captured, same
principle already planned for news scrapers.

**Strategic flag, not urgent but worth tracking:** a Maldives government
procurement modernization report describes the Beelan Portal as a stopgap the
government has stopped investing in, in favor of a planned unified e-GP
(e-Government Procurement) portal — Phase I of that includes "publish tender
notices and awards online." If/when that launches, it may become a better
single source than gazette.gov.mv (possibly with an actual API), worth
checking again periodically rather than building deep gazette-specific
tooling that assumes it's permanent.

**Discipline classifier, round 2:** re-tested against 10 more real titles
(HDC + Ministry of Finance tenders). Added "Real Estate & Leasing" as a
discipline bucket (confirmed necessary in round 1) and broadened IT keywords
after finding "Computer Systems & Laptops" was missed. Result: 6/10 correctly
bucketed on this pass, up from mostly "Other" before — "Cleaning Services,"
"Editorial Service," and "Safety Shoes and Gumboots" still correctly fall to
Other, which is honest, not a gap (they aren't construction/IT/medical/real
estate). Also fixed the notice-ID regex: found a third URL variant live,
`/iulaan/view/{id}`, alongside `/iulaan/{id}` and `/iulaan/print/{id}`.
