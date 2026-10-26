"""
Supabase Client and Object Storage Helper.

Provides optional integration with the Supabase Python SDK for:
- Supabase REST operations
- Supabase Object Storage (media, CV documents, company logos, photos)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("khulaasaa.supabase")

_SUPABASE_CLIENT: Any = None


def is_supabase_configured() -> bool:
    """Check if Supabase API URL and Key are configured."""
    has_url = bool(os.environ.get("SUPABASE_URL"))
    has_key = bool(
        os.environ.get("SUPABASE_SECRET_KEY")
        or os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    return has_url and has_key


def get_supabase_client() -> Optional[Any]:
    """Initialize or return the singleton Supabase client."""
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT

    url = os.environ.get("SUPABASE_URL")
    # Modern Supabase API keys: SUPABASE_SECRET_KEY (sb_secret_...) > legacy keys
    key = (
        os.environ.get("SUPABASE_SECRET_KEY")
        or os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        return None

    try:
        from supabase import create_client
        _SUPABASE_CLIENT = create_client(url, key)
        logger.info(f"Connected to Supabase client at {url}")
        return _SUPABASE_CLIENT
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def upload_media_to_supabase(
    bucket_name: str,
    file_bytes: bytes,
    destination_path: str,
    content_type: str = "image/png",
) -> Optional[str]:
    """
    Upload a binary file to a Supabase Storage bucket and return its public URL.
    Returns None if Supabase is not configured or upload fails.
    """
    client = get_supabase_client()
    if client is None:
        return None

    try:
        # Upload or update file in storage bucket
        client.storage.from_(bucket_name).upload(
            path=destination_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        # Retrieve public URL
        res = client.storage.from_(bucket_name).get_public_url(destination_path)
        return res
    except Exception as exc:
        logger.warning(f"Supabase storage upload error for '{destination_path}': {exc}")
        return None
