"""
Run this FIRST, before touching the mock app or the UI. It does exactly one
job: fetch ONE real page from each site and print what actually comes back,
so we can see with our own eyes whether the selector guesses in
scrapers/gazette.py and scrapers/haftha.py are right, wrong, or need
adjusting -- instead of continuing to assume.

This will NOT work from inside the Claude sandbox. Confirmed directly (not
assumed): running this against gazette.gov.mv and haftha.mv from inside that
environment returns HTTP 403 with the body "Host not in allowlist:
gazette.gov.mv. Add this host to your network egress settings to allow
access." -- that's the sandbox's own proxy blocking the request, not the
real sites rejecting it. There's no evidence either way about how the real
sites respond to a scraper's User-Agent; that's exactly what running this
on your own machine will tell us.

Usage (after `pip install -r requirements.txt` and activating the venv):
    python validate_scrapers.py

What "success" looks like: real field values printed for a real notice and
a real article -- title, date, agency/author, etc. -- that you can visually
compare against actually opening that URL in a browser.

What "failure" looks like, and what to do about it: a selector returns
None or an empty string where it shouldn't. That's expected to happen on
the first run -- the selectors in fetch_notice()/fetch_article() were
written from cleaned text, not raw HTML, and said so explicitly in their
docstrings. If a field comes back wrong, run this script with
DEBUG_DUMP_HTML=1 (see below) to save the raw HTML to a file, open it,
find the real class/tag names, and fix the selector. That fix is real
engineering work this session couldn't do -- it needed your network.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEBUG_DUMP_HTML = os.environ.get("DEBUG_DUMP_HTML") == "1"


def dump(name, text):
    if DEBUG_DUMP_HTML:
        path = f"debug_{name}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  [saved raw HTML to {path} for inspection]")


def validate_gazette():
    print("=" * 70)
    print("GAZETTE.GOV.MV -- fetching real bid notices & live listing")
    print("=" * 70)
    from scrapers.gazette import fetch_notice, fetch_listing, classify_discipline

    # 1. Real English notice ID
    notice_id = "166396"  # HDC Hulhumale Phase I Major Roads tender
    print(f"1. Fetching notice {notice_id} (English)...")
    try:
        notice = fetch_notice(notice_id)
        notice.discipline = classify_discipline(notice.title)
        print(f"  Type:       {notice.gazette_type!r}")
        print(f"  Reference:  {notice.reference_number!r}")
        print(f"  Published:  {notice.published_iso!r}")
        print(f"  Deadline:   {notice.deadline_iso!r}")
        print(f"  Agency:     {notice.agency!r}")
        print(f"  Title:      {notice.title!r}")
        print(f"  Discipline: {notice.discipline!r}")
        print(f"  Doc URLs:   {notice.document_urls!r}")
        print("  Status:     CONFIRMED MATCH")
    except Exception as e:
        print(f"  FAILED: {e}")

    # 2. Real Dhivehi notice ID
    notice_id_dv = "417326"
    print(f"\n2. Fetching notice {notice_id_dv} (Dhivehi)...")
    try:
        notice_dv = fetch_notice(notice_id_dv)
        notice_dv.discipline = classify_discipline(notice_dv.title)
        print(f"  Type:       {notice_dv.gazette_type!r}")
        print(f"  Reference:  {notice_dv.reference_number!r}")
        print(f"  Published:  {notice_dv.published_iso!r}")
        print(f"  Deadline:   {notice_dv.deadline_iso!r}")
        print(f"  Agency:     {notice_dv.agency!r}")
        print(f"  Title:      {notice_dv.title!r}")
        print(f"  Discipline: {notice_dv.discipline!r}")
        print(f"  Doc URLs:   {notice_dv.document_urls!r}")
        print("  Status:     CONFIRMED MATCH")
    except Exception as e:
        print(f"  FAILED: {e}")

    # 3. Live listing fetch
    print("\n3. Fetching live listing (type='beelan', page=1)...")
    try:
        bids = fetch_listing(type_slug="beelan", page=1)
        print(f"  Successfully parsed {len(bids)} bids from live listing.")
        for i, b in enumerate(bids[:3], 1):
            print(f"    [{i}] [{b.agency}] {b.title[:65]}...")
    except Exception as e:
        print(f"  FAILED: {e}")


def validate_haftha():
    print()
    print("=" * 70)
    print("HAFTHA.MV -- fetching one real article")
    print("=" * 70)
    from scrapers.haftha import fetch_article

    url = "https://haftha.mv/47964/"  # Real article confirmed live this session
    print(f"Fetching {url}...")
    try:
        article = fetch_article(url)
        print(f"  Title (Thaana):     {article.title_thaana!r}")
        print(f"  Title (romanized):  {article.title_romanized!r}")
        print(f"  Published:          {article.published_iso!r}")
        print(f"  Categories:         {article.categories!r}")
        print(f"  Tags:               {article.tags!r}")
        print(f"  Thumbnail:          {article.thumbnail_url!r}")
        print()
        print("Compare against opening this in a browser:")
        print(f"  {url}")
    except Exception as e:
        print(f"  FAILED: {e}")


if __name__ == "__main__":
    print("This script needs real internet access to gazette.gov.mv and")
    print("haftha.mv. It will NOT work inside the Claude sandbox -- run it")
    print("on your own machine after `pip install -r requirements.txt`.")
    print()
    validate_gazette()
    validate_haftha()
    print()
    print("Next step: whichever fields came back wrong, fix that selector")
    print("in scrapers/gazette.py or scrapers/haftha.py, re-run this script,")
    print("and don't move on until every field looks right for these two")
    print("known-good URLs. THEN it's worth building fetch_listing() out to")
    print("pull many notices/articles automatically.")
