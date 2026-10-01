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

DEBUG_DUMP_HTML = os.environ.get("DEBUG_DUMP_HTML") == "1"


def dump(name, text):
    if DEBUG_DUMP_HTML:
        path = f"debug_{name}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  [saved raw HTML to {path} for inspection]")


def validate_gazette():
    print("=" * 70)
    print("GAZETTE.GOV.MV -- fetching one real bid notice")
    print("=" * 70)
    from scrapers.gazette import fetch_notice

    # A real notice ID confirmed live during research this session.
    notice_id = "166396"  # HDC Hulhumale Phase I Major Roads tender
    print(f"Fetching notice {notice_id}...")
    try:
        notice = fetch_notice(notice_id)
        print(f"  Type:       {notice.gazette_type!r}")
        print(f"  Reference:  {notice.reference_number!r}")
        print(f"  Published:  {notice.published_iso!r}")
        print(f"  Deadline:   {notice.deadline_iso!r}")
        print(f"  Agency:     {notice.agency!r}  <- expect this to be EMPTY, flagged as unconfirmed selector")
        print(f"  Title:      {notice.title!r}")
        print(f"  Discipline: {notice.discipline!r}")
        print()
        print("Compare the above against opening this in a browser:")
        print(f"  {notice.url}")
        print("Every field except Agency should roughly match. Agency is the")
        print("one field the docstring flagged as an unconfirmed selector --")
        print("if it's empty, that's expected; go find the real markup and fix it.")
    except Exception as e:
        print(f"  FAILED: {e}")
        print("  This means either the network call itself failed (check your")
        print("  connection / whether the site blocked the request) or a")
        print("  selector crashed instead of just returning empty. Re-run with")
        print("  DEBUG_DUMP_HTML=1 python validate_scrapers.py to save the raw")
        print("  HTML and inspect it directly.")


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
