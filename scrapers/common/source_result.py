"""
Normalized scraper output contract and deterministic identifier helpers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Optional


def stable_digest(*parts: Optional[str], length: int = 16) -> str:
    """
    Compute a deterministic, process-independent SHA-256 hex digest from normalized strings.
    Replaces Python's salted built-in hash() for fallback record identifiers.
    """
    normalized_parts = [
        re.sub(r"\s+", " ", (part or "").strip().lower())
        for part in parts
        if part and str(part).strip()
    ]
    payload = "|".join(normalized_parts) if normalized_parts else "empty"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[: max(8, min(length, 64))]


def stable_record_id(prefix: str, *parts: Optional[str], length: int = 16) -> str:
    """
    Build a deterministic record identifier with a normalized slug prefix and SHA-256 suffix.
    """
    clean_prefix = re.sub(r"[^a-z0-9_-]+", "-", (prefix or "record").strip().lower()).strip("-") or "record"
    return f"{clean_prefix}-{stable_digest(*parts, length=length)}"


@dataclass
class SourceResult:
    """
    Normalized output contract returned by a scraper adapter before database persistence.
    A scraper fetches and parses external information; it does not save records or send alerts.
    """
    source_id: str
    external_id: str
    url: str
    extracted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    raw_content: Optional[str] = None
    normalized_content: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
