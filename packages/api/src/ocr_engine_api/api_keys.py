from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from ocr_engine_api.supabase_client import get_supabase_client

KEY_PREFIX = "ocr_live_"
KEY_HEX_LENGTH = 32  # bytes passed to secrets.token_hex; the key suffix is 64 hex chars


def generate_api_key() -> tuple[str, str, str]:
    """Generate an OCR API key and return (raw_key, key_hash, key_prefix).

    The raw key is shown to the user only once at creation time.
    The key_hash is stored in the database.
    The key_prefix is a visual identifier for listings.
    """
    raw_hex = secrets.token_hex(KEY_HEX_LENGTH)
    raw_key = f"{KEY_PREFIX}{raw_hex}"
    key_hash = hash_api_key(raw_key)
    key_prefix = f"{KEY_PREFIX}{raw_hex[:8]}..."
    return raw_key, key_hash, key_prefix


def hash_api_key(key: str) -> str:
    """Return the SHA-256 hash of an API key."""
    return hashlib.sha256(key.encode()).hexdigest()


def store_api_key(account_id: str, key_hash: str, key_prefix: str, name: str = "default") -> dict:
    """Insert a new API key record in Supabase and return the stored row."""
    client = get_supabase_client()
    result = (
        client.table("api_keys")
        .insert({
            "account_id": account_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": name,
        })
        .execute()
    )
    return result.data[0] if result.data else {}


def delete_api_key(key_id: str, account_id: str) -> dict:
    """Delete an API key row. Returns the deleted row when available."""
    client = get_supabase_client()
    result = (
        client.table("api_keys")
        .delete()
        .eq("id", key_id)
        .eq("account_id", account_id)
        .execute()
    )
    return result.data[0] if result.data else {}


def list_api_keys(account_id: str) -> list[dict]:
    """List API keys for an account. Returns prefix, name, status, timestamps only."""
    client = get_supabase_client()
    result = (
        client.table("api_keys")
        .select("id, key_prefix, name, status, created_at, last_used_at, revoked_at")
        .eq("account_id", account_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


ACCOUNT_COLUMNS = "id, email, role, status, plan, assigned_demo, created_at, accepted_at, invited_at, supabase_user_id"


def get_account_by_supabase_user_id(supabase_user_id: str) -> dict | None:
    """Look up an account by its Supabase user ID."""
    client = get_supabase_client()
    result = (
        client.table("accounts")
        .select(ACCOUNT_COLUMNS)
        .eq("supabase_user_id", supabase_user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def get_account_by_id(account_id: str) -> dict | None:
    """Look up an account by its internal ID."""
    client = get_supabase_client()
    result = (
        client.table("accounts")
        .select(ACCOUNT_COLUMNS)
        .eq("id", account_id)
        .execute()
    )
    return result.data[0] if result.data else None


def list_accounts() -> list[dict]:
    """List all accounts (admin use). Emails are included for the admin picker."""
    client = get_supabase_client()
    result = (
        client.table("accounts")
        .select(ACCOUNT_COLUMNS)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def find_active_key_by_hash(key_hash: str) -> dict | None:
    """Find an active API key by its hash. Returns the key row or None."""
    client = get_supabase_client()
    result = (
        client.table("api_keys")
        .select("id, account_id, key_prefix, name, status, last_used_at")
        .eq("key_hash", key_hash)
        .eq("status", "active")
        .execute()
    )
    return result.data[0] if result.data else None


def update_last_used_at(key_id: str) -> None:
    """Fire-and-forget update of last_used_at for an API key."""
    client = get_supabase_client()
    client.table("api_keys").update({
        "last_used_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", key_id).execute()
