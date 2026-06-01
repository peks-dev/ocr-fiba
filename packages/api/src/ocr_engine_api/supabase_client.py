from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from ocr_engine_api.settings import get_api_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return a cached Supabase client using the service role key.

    Requires SUPABASE_URL and SUPABASE_SERVICE_KEY to be configured.
    The service role key bypasses RLS, so this client must only be used
    server-side — never exposed to the browser or API responses.
    """
    settings = get_api_settings()
    if not settings.has_supabase:
        raise RuntimeError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    return create_client(settings.supabase_url, settings.supabase_service_key)
