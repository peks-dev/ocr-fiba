#!/usr/bin/env python3
"""Create a dedicated tester account and issue an ocr_live_ API key.

The raw key is written only to --output (chmod 600) and is never printed to
stdout or stderr. A non-secret prefix and the output path are printed to
stderr so the operator can confirm success.

Usage:
  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... \
    python scripts/issue_api_key.py --email agentic-os@example.com --output /path/to/key

The account uses role='tester' (the schema has no separate service role) and
assigned_demo='player' unless overridden. If the Auth user already exists, a
new named key is added to the matching account. This script is intentionally
not wired to print or log the secret; do not change that.
"""
from __future__ import annotations

import argparse
import os
import secrets
import stat
import sys
from pathlib import Path
from typing import Any

from supabase import create_client

from ocr_engine_api.api_keys import generate_api_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Issue an OCR API key to a file.")
    parser.add_argument("--email", required=True, help="Account email (created if missing)")
    parser.add_argument("--output", required=True, type=Path, help="File path that will receive the raw key")
    parser.add_argument("--name", default="agentic-os", help="API key name (default: agentic-os)")
    parser.add_argument(
        "--assigned-demo",
        default="player",
        choices=("referee", "player", "club"),
        help="Required tester demo assignment (schema has no service role)",
    )
    return parser.parse_args()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Missing required env var: {name}", file=sys.stderr)
        sys.exit(2)
    return value


def find_user_by_email(supabase: Any, email: str) -> dict[str, Any] | None:
    page = 1
    while True:
        result = supabase.auth.admin.list_users(page=page, per_page=100)
        users = getattr(result, "users", None) or []
        for user in users:
            user_email = getattr(user, "email", None) or (user.get("email") if isinstance(user, dict) else None)
            if user_email and user_email.lower() == email.lower():
                return user if isinstance(user, dict) else user.model_dump()
        if len(users) < 100:
            return None
        page += 1


def resolve_user_id(user: Any) -> str | None:
    if isinstance(user, dict):
        return user.get("id")
    return getattr(user, "id", None)


def main() -> int:
    args = parse_args()
    email = args.email.strip().lower()
    if not email:
        print("Email is required", file=sys.stderr)
        return 2

    output: Path = args.output.expanduser()
    if output.exists() and output.is_dir():
        print("Output path must be a file, not a directory", file=sys.stderr)
        return 2

    supabase = create_client(require_env("SUPABASE_URL"), require_env("SUPABASE_SERVICE_KEY"))
    user = find_user_by_email(supabase, email)

    if user is None:
        # Random password is discarded; this account authenticates with the API key.
        created = supabase.auth.admin.create_user({
            "email": email,
            "password": secrets.token_urlsafe(32),
            "email_confirm": True,
            "app_metadata": {"role": "tester"},
            "user_metadata": {"assigned_demo": args.assigned_demo, "name": args.name},
        })
        raw_user = getattr(created, "user", None) or getattr(created, "data", None) or created
        user = raw_user if isinstance(raw_user, dict) else raw_user.model_dump()
        print(f"Created Auth user for {email}", file=sys.stderr)

    user_id = resolve_user_id(user)
    if not user_id:
        print("Could not resolve Auth user id", file=sys.stderr)
        return 1

    account_result = (
        supabase.table("accounts")
        .select("id, role, status")
        .eq("supabase_user_id", user_id)
        .execute()
    )
    account = account_result.data[0] if account_result.data else None
    if account is None:
        upsert = (
            supabase.table("accounts")
            .upsert(
                {
                    "supabase_user_id": user_id,
                    "email": email,
                    "role": "tester",
                    "assigned_demo": args.assigned_demo,
                    "status": "active",
                },
                on_conflict="supabase_user_id",
            )
            .execute()
        )
        account = upsert.data[0] if upsert.data else None
    if not account or not account.get("id"):
        print("Could not resolve account id", file=sys.stderr)
        return 1
    if account.get("status") and account["status"] != "active":
        print("Account is not active", file=sys.stderr)
        return 1

    raw_key, key_hash, key_prefix = generate_api_key()
    stored = (
        supabase.table("api_keys")
        .insert({
            "account_id": account["id"],
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": args.name,
        })
        .execute()
    )
    if not stored.data:
        print("Failed to store API key", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(raw_key)
            handle.write("\n")
    except OSError as exc:
        print(f"Failed to write key file: {exc}", file=sys.stderr)
        return 1
    os.chmod(output, stat.S_IRUSR | stat.S_IWUSR)

    print(f"Wrote API key {key_prefix} to {output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
