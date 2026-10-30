"""
Normalized scraper output contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


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
