#!/usr/bin/env python3
"""Create or update a Supabase Auth user as an OCR admin.

Usage:
  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python scripts/create_admin_user.py admin@example.com --password 'change-me'

If the Auth user already exists, the script updates the matching account row to
role='admin' and assigned_demo=NULL. A password is required only when creating a
new user.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from supabase import create_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or promote a FIBA OCR admin user in Supabase.")
    parser.add_argument("email", help="Admin email address")
    parser.add_argument("--password", help="Password to set when creating the Auth user")
    parser.add_argument("--email-confirm", action="store_true", default=True, help="Mark newly-created user's email as confirmed")
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


def main() -> int:
    args = parse_args()
    email = args.email.strip().lower()
    if not email:
        print("Email is required", file=sys.stderr)
        return 2

    supabase = create_client(require_env("SUPABASE_URL"), require_env("SUPABASE_SERVICE_KEY"))
    user = find_user_by_email(supabase, email)

    if user is None:
      if not args.password:
          print("--password is required when creating a new Auth user", file=sys.stderr)
          return 2
      created = supabase.auth.admin.create_user({
          "email": email,
          "password": args.password,
          "email_confirm": args.email_confirm,
          "user_metadata": {"role": "admin"},
      })
      raw_user = getattr(created, "user", None) or getattr(created, "data", None) or created
      user = raw_user if isinstance(raw_user, dict) else raw_user.model_dump()
      print(f"Created Auth user for {email}")
    else:
      print(f"Found existing Auth user for {email}")

    user_id = user.get("id")
    if not user_id:
        print("Could not resolve Auth user id", file=sys.stderr)
        return 1

    response = (
        supabase.table("accounts")
        .upsert({
            "supabase_user_id": user_id,
            "email": email,
            "role": "admin",
            "assigned_demo": None,
            "status": "active",
        }, on_conflict="supabase_user_id")
        .execute()
    )
    print(f"Promoted {email} ({user_id}) to accounts.role='admin'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
