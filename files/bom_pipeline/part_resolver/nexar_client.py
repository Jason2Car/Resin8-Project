"""
Octopart's API is now Nexar (GraphQL, OAuth2 client-credentials). This is
written against the real Nexar API - it'll work as-is once you have a
NEXAR_CLIENT_ID / NEXAR_CLIENT_SECRET and network access, both absent in
this sandbox, so `_client()` returns None here and callers fail closed
(treated as "no match", not silently skipped - see resolve.py).

Sign up / API docs: https://nexar.com/api
"""
import os
import time

TOKEN_URL = "https://identity.nexar.com/connect/token"
GRAPHQL_URL = "https://api.nexar.com/graphql"

_token_cache = {"token": None, "expires_at": 0}


def _get_token():
    client_id = os.environ.get("NEXAR_CLIENT_ID")
    client_secret = os.environ.get("NEXAR_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    import requests
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    })
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    return _token_cache["token"]


def lookup_by_mpn(mpn: str):
    """Exact lookup by manufacturer part number.
    Returns {manufacturer, description, mpn} or None if not found / no access."""
    token = _get_token()
    if not token:
        return None

    import requests
    query = """
    query($mpn: String!) {
      supSearchMpn(q: $mpn, limit: 1) {
        results {
          part { mpn manufacturer { name } shortDescription }
        }
      }
    }
    """
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": {"mpn": mpn}},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    results = resp.json().get("data", {}).get("supSearchMpn", {}).get("results", [])
    if not results:
        return None
    part = results[0]["part"]
    return {
        "manufacturer": part["manufacturer"]["name"],
        "description": part["shortDescription"],
        "mpn": part["mpn"],
    }


def search_by_description(description: str, limit: int = 3):
    """Free-text search, used when there's no part number to look up exactly."""
    token = _get_token()
    if not token:
        return []

    import requests
    query = """
    query($q: String!, $limit: Int!) {
      supSearch(q: $q, limit: $limit) {
        results {
          part { mpn manufacturer { name } shortDescription }
        }
      }
    }
    """
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": {"q": description, "limit": limit}},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    results = resp.json().get("data", {}).get("supSearch", {}).get("results", [])
    return [
        {
            "manufacturer": r["part"]["manufacturer"]["name"],
            "description": r["part"]["shortDescription"],
            "mpn": r["part"]["mpn"],
        }
        for r in results
    ]
