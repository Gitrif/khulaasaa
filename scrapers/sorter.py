"""
The "sort" stage of grab -> sort -> dedupe, deliberately its own module so
no scraper needs to change when the classifier does.

A Classifier is just: Callable[[str], str] -- takes a title, returns a label.
Anything matching that signature works with classify_notices() in
scrapers/gazette.py (and the same pattern applies to haftha.py's narrative
tagging once that's built). Two implementations are provided:

- keyword_classify() in scrapers/gazette.py -- free, instant, already
  tested against real data, but limited (see scrapers/README.md's "6/10"
  result).
- claude_classify() below -- costs an API call per title, but should
  handle the ambiguous cases keywords can't (e.g. "Providing Cleaning
  Services", which round-2 testing showed keywords correctly leave as
  "Other" but a model could plausibly place more precisely).

NOT YET TESTED against real output -- this needs a real ANTHROPIC_API_KEY
and was written, not run, this session (no billing credential available
here). Before trusting it: run it against the same batch of real titles
scrapers/README.md already used for the keyword classifier, and compare
results side by side. That comparison is real work still to do, not
assumed to favor the LLM version by default.
"""
from __future__ import annotations

from typing import Callable, Optional

Classifier = Callable[[str], str]


def claude_classify(
    title: str,
    labels: list[str],
    api_key: Optional[str] = None,
    model: str = "claude-sonnet-4-5",
) -> str:
    """
    LLM-backed classifier matching the Classifier signature (once `labels`
    and the rest are bound via functools.partial -- see make_claude_classifier
    below for the form that actually plugs into classify_notices()).

    Deliberately plain: one title in, one label out, forced to one of the
    given `labels` via the prompt. No batching, no caching, no retry logic
    -- all real gaps if this goes into production at any volume. At even
    a few hundred bids, call-per-title is the wrong shape; batch N titles
    per call instead. That's a concrete next step, not done here.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)  # reads ANTHROPIC_API_KEY env var if None
    label_list = ", ".join(labels)
    resp = client.messages.create(
        model=model,
        max_tokens=20,
        messages=[{
            "role": "user",
            "content": (
                f"Classify this government bid/tender title into exactly one "
                f"of these categories: {label_list}.\n\n"
                f'Title: "{title}"\n\n'
                f"Reply with only the category name, nothing else."
            ),
        }],
    )
    result = resp.content[0].text.strip()
    return result if result in labels else "Other"


def make_claude_classifier(
    labels: list[str], api_key: Optional[str] = None, model: str = "claude-sonnet-4-5"
) -> Classifier:
    """Bind labels/api_key/model so the result matches the plain
    Classifier signature (title) -> str, ready to pass straight into
    gazette.classify_notices(notices, classifier=...)."""
    def _classify(title: str) -> str:
        return claude_classify(title, labels=labels, api_key=api_key, model=model)
    return _classify
