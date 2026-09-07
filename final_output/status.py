"""
The brief's output spec (item 8) wants every line to say plainly whether
it's a firm quote, an estimate, a substitution, or a failure to source -
this is where those four buckets get decided, from signals already computed
by earlier stages rather than a new judgment call:

  UNSOURCED    - Stage 2/3 never found a supplier at all, OR a supplier was
                 found but no contact/login method exists for them yet
                 (Stage 3's UNEXPLORED_SOURCE) - both are "no quote is
                 possible right now," just for different reasons, which the
                 detail message distinguishes
  SUBSTITUTION - an equivalent part was used, not the exact one requested
                 (match_confidence != EXACT_MATCH) - true regardless of
                 whether a price came back, since "which part" and "what
                 price" are separate questions
  FIRM_QUOTE   - exact part, approved vendor, and an actual price in hand
  ESTIMATE     - anything else: exact part but qualification still pending,
                 or a price hasn't come back yet
"""


def classify(vendor_status: str, match_confidence: str, unit_price) -> tuple:
    """Returns (status, detail)."""
    if vendor_status == "UNSOURCED":
        return "UNSOURCED", "No supplier could be identified for this line."

    if vendor_status == "UNEXPLORED_SOURCE":
        return ("UNSOURCED", "A likely part/manufacturer match exists, but no contact method or portal login "
                "has been established for this supplier - unexplored source, needs manual outreach before "
                "it can be qualified or quoted.")

    if match_confidence != "EXACT_MATCH":
        detail = "Quote is for an equivalent part, not an exact match to the BOM line - needs engineering sign-off."
        if unit_price is None:
            detail += " Price not yet received."
        return "SUBSTITUTION", detail

    if unit_price is None:
        return "ESTIMATE", "Exact part identified, but no price has been received yet."

    if vendor_status == "NEEDS_QUALIFICATION":
        return "ESTIMATE", "Exact part and price in hand, but supplier qualification is still pending."

    return "FIRM_QUOTE", "Exact part, approved supplier, price in hand - ready to transact."
