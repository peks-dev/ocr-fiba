from __future__ import annotations

from fastapi import APIRouter, Depends

from ocr_engine_api.api_keys import (
    delete_api_key as delete_api_key_record,
    generate_api_key,
    get_account_by_id,
    get_account_by_supabase_user_id,
    list_accounts,
    list_api_keys,
    store_api_key,
)
from ocr_engine_api.auth_api_key import invalidate_api_key_cache
from ocr_engine_api.auth_supabase import require_supabase_user
from ocr_engine_api.errors import error_response

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def require_admin_account(user: dict = Depends(require_supabase_user)) -> dict:
    """Resolve the caller's account and require accounts.role == 'admin'."""
    supabase_uid = user.get("sub")
    if not supabase_uid:
        raise error_response(401, "UNAUTHORIZED", "Invalid token: missing sub claim")
    account = get_account_by_supabase_user_id(str(supabase_uid))
    if not account:
        raise error_response(404, "ACCOUNT_NOT_FOUND", "Account not found. Signup may not have completed.")
    if account.get("status") != "active":
        raise error_response(403, "FORBIDDEN", "Account is not active")
    if account.get("role") != "admin":
        raise error_response(403, "FORBIDDEN", "Admin role required")
    return account


@router.get("/accounts")
async def get_accounts(_admin: dict = Depends(require_admin_account)) -> dict:
    """List all accounts so an admin can issue keys for testers or service accounts."""
    return {"success": True, "accounts": list_accounts()}


@router.get("/accounts/{account_id}/api-keys")
async def get_account_api_keys(account_id: str, _admin: dict = Depends(require_admin_account)) -> dict:
    account = get_account_by_id(account_id)
    if not account:
        raise error_response(404, "ACCOUNT_NOT_FOUND", "Account not found")
    return {"success": True, "account_id": account_id, "keys": list_api_keys(account_id)}


@router.post("/accounts/{account_id}/api-keys")
async def create_account_api_key(
    account_id: str,
    name: str = "default",
    _admin: dict = Depends(require_admin_account),
) -> dict:
    """Create a named API key for another account. The raw key is returned once."""
    account = get_account_by_id(account_id)
    if not account:
        raise error_response(404, "ACCOUNT_NOT_FOUND", "Account not found")
    if account.get("status") != "active":
        raise error_response(403, "FORBIDDEN", "Target account is not active")

    raw_key, key_hash, key_prefix = generate_api_key()
    store_api_key(account_id, key_hash, key_prefix, name=name)
    return {
        "success": True,
        "key": raw_key,
        "key_prefix": key_prefix,
        "name": name,
        "account_id": account_id,
        "message": "Store this key securely. It will not be shown again.",
    }


@router.delete("/accounts/{account_id}/api-keys/{key_id}")
async def delete_account_api_key(
    account_id: str,
    key_id: str,
    _admin: dict = Depends(require_admin_account),
) -> dict:
    """Permanently delete an API key belonging to the given account."""
    account = get_account_by_id(account_id)
    if not account:
        raise error_response(404, "ACCOUNT_NOT_FOUND", "Account not found")
    result = delete_api_key_record(key_id, account_id)
    if not result:
        raise error_response(404, "API_KEY_NOT_FOUND", "API key not found or does not belong to this account")
    invalidate_api_key_cache(account_id=account_id)
    return {"success": True, "key_id": key_id, "account_id": account_id, "status": "deleted"}
