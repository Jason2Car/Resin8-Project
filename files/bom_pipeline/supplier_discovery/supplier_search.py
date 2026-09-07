"""
For NO_MATCH lines: Stage 2 couldn't find the part in any catalog at all,
so there's nothing to check coverage against - this needs sourcing from
scratch. Real approach: query structured supplier directories (Thomasnet,
industry-specific directories) and distributor sites, falling back to
general web search only for genuinely niche manufacturers - per the earlier
architecture discussion, general web search should be the fallback, not the
primary mechanism, since it's slower and harder to audit.

No backend wired in here (matches mechanical_search.py's gap) - this always
returns [], and pipeline_stage3.py treats an empty result as "needs manual
sourcing," not as a dead end.
"""


def find_suppliers(description: str, limit: int = 3) -> list:
    """Returns [{supplier_name, source, url}, ...]. Empty when no backend
    is configured."""
    return []
