from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ocr_engine_api.api_keys import (
    generate_api_key,
    get_account_by_supabase_user_id,
    list_api_keys,
    delete_api_key as delete_api_key_record,
    store_api_key,
)
from ocr_engine_api.auth_supabase import require_supabase_user
from ocr_engine_api.errors import error_response

router = APIRouter(prefix="/v1/me", tags=["me"])


def _get_account_id(user: dict) -> str:
    """Resolve the internal account ID from a Supabase JWT payload."""
    supabase_uid = user.get("sub")
    if not supabase_uid:
        raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
    account = get_account_by_supabase_user_id(supabase_uid)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found. Signup may not have completed.")
    if account.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    return account["id"]


@router.post("/api-keys/bootstrap")
async def bootstrap_api_key(user: dict = Depends(require_supabase_user)) -> dict:
    """Create the first API key for the authenticated user.

    Returns the raw key once — it cannot be retrieved again.
    """
    account_id = _get_account_id(user)

    existing = list_api_keys(account_id)
    active_keys = [k for k in existing if k.get("status") == "active"]
    if active_keys:
        raise error_response(409, "API_KEY_ALREADY_EXISTS", "An active API key already exists. Use POST /v1/me/api-keys to create additional keys.")

    raw_key, key_hash, key_prefix = generate_api_key()
    store_api_key(account_id, key_hash, key_prefix, name="default")

    return {
        "success": True,
        "key": raw_key,
        "key_prefix": key_prefix,
        "message": "Store this key securely. It will not be shown again.",
    }


@router.get("/api-keys")
async def get_api_keys(user: dict = Depends(require_supabase_user)) -> dict:
    """List API keys for the authenticated user. Only shows prefixes, never full keys."""
    account_id = _get_account_id(user)
    keys = list_api_keys(account_id)
    return {"success": True, "keys": keys}


@router.post("/api-keys")
async def create_api_key(
    name: str = "default",
    user: dict = Depends(require_supabase_user),
) -> dict:
    """Create an additional API key with a custom name."""
    account_id = _get_account_id(user)
    raw_key, key_hash, key_prefix = generate_api_key()
    store_api_key(account_id, key_hash, key_prefix, name=name)

    return {
        "success": True,
        "key": raw_key,
        "key_prefix": key_prefix,
        "name": name,
        "message": "Store this key securely. It will not be shown again.",
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    user: dict = Depends(require_supabase_user),
) -> dict:
    """Delete an API key by its ID."""
    account_id = _get_account_id(user)
    result = delete_api_key_record(key_id, account_id)
    if not result:
        raise error_response(404, "API_KEY_NOT_FOUND", "API key not found or does not belong to this account")
    return {"success": True, "key_id": key_id, "status": "deleted"}
