"""
Split into two passes on purpose:
  1. find_candidate() - per line, cheap, local: hits the catalog backend.
  2. (in pipeline_stage2.py) every line whose candidate came from an exact
     unit-id lookup gets batched into ONE llm.check_part_plausibility() call,
     same batching discipline as stage 1's reasoning check.

Lines resolved by description search are already labeled PROBABLE_EQUIVALENT
by construction (no unit id was verified) - no plausibility gate needed on
top, the "needs engineering sign-off" note already covers it.
"""
from router import classify_line


def find_candidate(name: str, unit_id: str, specs: str, electronic_backend, mechanical_backend):
    """Returns one of:
      {"category", "source": "exact_id", "resolved_unit_id", "manufacturer", "catalog_description", "purchase_url"}
      {"category", "source": "description_search", ...same fields...}
      {"category", "source": "none"}
    Plausibility of an exact_id hit is NOT judged here - see pipeline_stage2.py.
    purchase_url is "" whenever the backend didn't return one (true for every
    mechanical hit today, and for electronics results with no offer link) -
    Stage 6 falls back to portal/email contact when this is empty.
    """
    category = classify_line(name, specs)
    backend = electronic_backend if category == "ELECTRONIC" else mechanical_backend

    if unit_id:
        lookup_fn = getattr(backend, "lookup_by_mpn", None)
        exact = lookup_fn(unit_id) if lookup_fn else None
        if exact:
            return {"category": category, "source": "exact_id",
                    "resolved_unit_id": exact["mpn"], "manufacturer": exact["manufacturer"],
                    "catalog_description": exact["description"], "purchase_url": exact.get("buy_url", "")}

    search_fn = getattr(backend, "search_by_description", None)
    candidates = search_fn(name) if search_fn else []
    if candidates:
        top = candidates[0]
        return {"category": category, "source": "description_search",
                "resolved_unit_id": top["mpn"], "manufacturer": top["manufacturer"],
                "catalog_description": top["description"], "purchase_url": top.get("buy_url", "")}

    return {"category": category, "source": "none",
            "resolved_unit_id": "", "manufacturer": "", "catalog_description": "", "purchase_url": ""}
