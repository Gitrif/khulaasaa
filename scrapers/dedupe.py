"""
Cross-source deduplication for bid/tender records.

Why this exists: gazette.gov.mv is the confirmed primary discovery source
(see scrapers/README.md), but agency sites like hdc.com.mv publish the same
tenders too -- and once council sites are added, the same tender could
plausibly surface from three places. Without a dedup key, the bids page
shows the same tender 2-3 times. This module is the merge layer that has
to exist before a second source is wired in, not after.

STRATEGY
1. Primary key: the procurement/reference number every real notice carries
   (e.g. "HDC (161)-PRO/IU/2021/168", "TES/2020/W-021"). Confirmed present
   and stable across sources this session -- HDC's own site and its
   gazette.gov.mv notice quote the identical reference number. Normalize
   (uppercase, strip whitespace) before comparing, since the same number
   was seen with and without a space before "(161)" in different notices.
2. Fallback key, used only when a record has no parseable reference number
   (seen on a few older/informal notices): (agency, normalized title,
   published date within a 3-day window). Looser and deliberately
   conservative -- would rather leave two records unmerged than wrongly
   merge two different tenders from the same agency published close
   together.
3. When records merge, keep the earliest published_iso (first public
   appearance), keep the union of every field across sources (fill gaps --
   e.g. gazette may have the deadline, HDC's own page may have the actual
   document links), and record every contributing source so the bids page
   can show "Also published on: HDC, Gazette.mv" rather than hiding the
   agency's own richer listing entirely.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional, Callable, Any


def normalize_reference(ref: str) -> str:
    """Collapse formatting variants of the same reference number to one
    comparable key. Confirmed necessary: the same tender's reference
    number appeared both as "HDC (161)-..." and "HDC(161)-..." across
    different real notices this session."""
    ref = ref.upper().strip()
    ref = re.sub(r"\s+", "", ref)
    ref = re.sub(r"[\u200B\u200E\u200F]", "", ref)  # invisible chars, common in pasted PDF text
    return ref


def normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"&", " and ", t)
    t = re.sub(r"[^\w\s]", "", t)   # drop punctuation
    t = re.sub(r"\s+", " ", t)
    return t.strip()


@dataclass
class SourceRecord:
    """One agency/site's copy of a bid notice."""
    source_name: str            # e.g. "gazette.gov.mv", "hdc.com.mv"
    source_url: str
    reference_number: Optional[str]
    agency: str
    title: str
    published_iso: Optional[str]
    deadline_iso: Optional[str]
    document_urls: list[str] = field(default_factory=list)
    submission_location: Optional[str] = None
    info_date: Optional[str] = None
    info_location: Optional[str] = None


@dataclass
class MergedBid:
    """The canonical, de-duplicated record the bids page actually renders."""
    reference_number: Optional[str]
    agency: str
    title: str
    published_iso: Optional[str]
    deadline_iso: Optional[str]
    discipline: Optional[str] = None
    sources: list[SourceRecord] = field(default_factory=list)
    submission_location: Optional[str] = None
    info_date: Optional[str] = None
    info_location: Optional[str] = None

    @property
    def source_names(self) -> list[str]:
        return [s.source_name for s in self.sources]

    @property
    def all_document_urls(self) -> list[str]:
        urls = []
        for s in self.sources:
            urls.extend(s.document_urls)
        return list(dict.fromkeys(urls))

    @property
    def is_open(self) -> bool:
        if not self.deadline_iso:
            return True
        try:
            deadline = datetime.fromisoformat(self.deadline_iso)
            now = datetime.now(deadline.tzinfo) if deadline.tzinfo else datetime.now()
            return deadline > now
        except Exception:
            return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation matching the UI/API expectations."""
        primary_source = self.sources[0] if self.sources else None
        return {
            "ref": self.reference_number,
            "agency": self.agency,
            "title": self.title,
            "published_iso": self.published_iso,
            "deadline_iso": self.deadline_iso,
            "discipline": self.discipline or "Other",
            "is_open": self.is_open,
            "source_names": self.source_names,
            "document_urls": self.all_document_urls,
            "source_url": primary_source.source_url if primary_source else "",
            "submission_location": self.submission_location,
            "info_date": self.info_date,
            "info_location": self.info_location,
        }


def _fallback_match(a: SourceRecord, b: SourceRecord) -> bool:
    if a.agency.strip().lower() != b.agency.strip().lower():
        return False
    if normalize_title(a.title) != normalize_title(b.title):
        return False
    if not (a.published_iso and b.published_iso):
        return True  # can't compare dates, but agency+title already matched exactly
    try:
        da = datetime.fromisoformat(a.published_iso).date()
        db = datetime.fromisoformat(b.published_iso).date()
    except ValueError:
        return True
    return abs((da - db)) <= timedelta(days=3)


def merge_records(records: list[SourceRecord]) -> list[MergedBid]:
    """Group SourceRecords into de-duplicated MergedBid entries."""
    by_ref: dict[str, list[SourceRecord]] = {}
    unkeyed: list[SourceRecord] = []

    for r in records:
        if r.reference_number:
            key = normalize_reference(r.reference_number)
            by_ref.setdefault(key, []).append(r)
        else:
            unkeyed.append(r)

    merged: list[MergedBid] = []
    for key, group in by_ref.items():
        merged.append(_build_merged(group))

    # Fallback matching for records with no reference number: greedily
    # group by (agency, title, date-proximity). O(n^2) but this list
    # should be small (only records missing a ref number reach here).
    used = [False] * len(unkeyed)
    for i, r in enumerate(unkeyed):
        if used[i]:
            continue
        group = [r]
        used[i] = True
        for j in range(i + 1, len(unkeyed)):
            if not used[j] and _fallback_match(r, unkeyed[j]):
                group.append(unkeyed[j])
                used[j] = True
        merged.append(_build_merged(group))

    return merged


def _build_merged(group: list[SourceRecord]) -> MergedBid:
    earliest = min(
        (g for g in group if g.published_iso),
        key=lambda g: g.published_iso,
        default=group[0],
    )
    # Prefer a deadline if any source has one (agency sites and gazette
    # don't always both carry it).
    deadline = next((g.deadline_iso for g in group if g.deadline_iso), None)
    submission_loc = next((g.submission_location for g in group if g.submission_location), None)
    info_dt = next((g.info_date for g in group if g.info_date), None)
    info_loc = next((g.info_location for g in group if g.info_location), None)
    return MergedBid(
        reference_number=next((g.reference_number for g in group if g.reference_number), None),
        agency=earliest.agency,
        title=earliest.title,
        published_iso=earliest.published_iso,
        deadline_iso=deadline,
        sources=group,
        submission_location=submission_loc,
        info_date=info_dt,
        info_location=info_loc,
    )


def aggregate_bids(
    records: list[SourceRecord | Any],
    classifier: Optional[Callable[[str], str]] = None,
) -> list[MergedBid]:
    """
    End-to-end bids aggregation:
    Takes SourceRecords or objects with a .to_source_record() method (like BidNotice),
    merges duplicates across sources, classifies disciplines, and returns canonical MergedBids.
    """
    normalized_records: list[SourceRecord] = []
    for r in records:
        if isinstance(r, SourceRecord):
            normalized_records.append(r)
        elif hasattr(r, "to_source_record"):
            normalized_records.append(r.to_source_record())
        elif isinstance(r, dict):
            normalized_records.append(
                SourceRecord(
                    source_name=r.get("source_name", "unknown"),
                    source_url=r.get("source_url", ""),
                    reference_number=r.get("reference_number") or r.get("ref"),
                    agency=r.get("agency", ""),
                    title=r.get("title", ""),
                    published_iso=r.get("published_iso"),
                    deadline_iso=r.get("deadline_iso"),
                    document_urls=r.get("document_urls", []),
                    submission_location=r.get("submission_location"),
                    info_date=r.get("info_date"),
                    info_location=r.get("info_location"),
                )
            )
        else:
            raise TypeError(f"Unsupported record type: {type(r)}")

    merged = merge_records(normalized_records)

    if classifier:
        for bid in merged:
            bid.discipline = classifier(bid.title)

    return merged
