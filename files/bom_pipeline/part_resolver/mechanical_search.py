"""
There's no aggregator API for mechanical/hardware parts the way Octopart
covers electronics. What's realistic:
  - Some distributors (McMaster-Carr, Grainger) expose punchout/EDI catalogs
    for procurement systems, not a public "search by keyword" REST endpoint.
  - The practical path is a general web/product search API (Bing Web Search,
    SerpAPI, or similar) scoped to known distributor domains, then an LLM
    pass to extract a candidate part number + price/lead-time page from the
    results - this is closer to Stage 3 (supplier discovery) than a clean
    lookup, and confidence should reflect that.

This module defines the interface as a pluggable backend so resolve.py
doesn't care which search provider is wired in. No backend is wired in this
sandbox (no network) - see mock_catalog.py for the offline stand-in used to
demonstrate the resolution logic.
"""


def search(description: str, limit: int = 3) -> list:
    """Returns [{source, title, url, snippet}, ...]. Real implementation:
    call your search provider scoped to distributor domains, e.g.
    site:mcmaster.com OR site:grainger.com OR site:store.mfg.com, then let
    an LLM pull a candidate part number out of the top results.
    Returns [] when no backend is configured - resolve.py treats an empty
    result as NO_MATCH, not as an error to guess around."""
    return []
