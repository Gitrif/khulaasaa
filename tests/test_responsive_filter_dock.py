"""Static guards for the responsive filter dock and Janaza icon."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_filter_toolbar_surface_defined_once():
    css = _read("static/css/components.css")
    assert css.count("\n.filter-toolbar {") == 1


def test_news_filter_markup_appears_once_and_keeps_query_params():
    html = _read("templates/index.html")
    assert html.count('id="pageFilterToolbar"') == 1
    assert html.count('id="filterDrawer"') == 1
    assert "/?tag=" in html and "/?topic=" in html
    assert 'aria-expanded="false"' in html


def test_janaza_mobile_nav_uses_crescent_not_plus():
    html = _read("templates/base.html")
    start = html.index('href="/obituaries" class="mobile-nav-item')
    block = html[start:start + 600]
    assert "M20.985 12.486" in block
    assert "M12 4v16m-6-10h12" not in block
