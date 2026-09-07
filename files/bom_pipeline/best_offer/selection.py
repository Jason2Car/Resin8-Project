"""
Deliberately doesn't make the business call of "price matters more than
lead time" - that's not an engineering decision, it's a procurement policy
one, and the brief's neutrality requirement means whatever weighting is used
has to be something the client can see and adjust, not something baked in
silently. This module computes the comparable factors and a score from
whatever weights it's given; DEFAULT_WEIGHTS below is a placeholder to make
the demo runnable, not a recommendation.

Only meaningfully exercised once a line has more than one candidate quote -
Stage 2/3's known limitation (one supplier per line) means most lines here
will only ever have one candidate to "compare," which trivially wins. The
scoring path is written to handle N candidates once that upstream limitation
is addressed.
"""

DEFAULT_WEIGHTS = {"price": 0.5, "lead_time": 0.3, "qualification": 0.2}  # tune freely


def _normalize(values, lower_is_better=True):
    """Min-max normalize to 0-1 within THIS line's candidate set only -
    comparing candidates against each other, never against some fixed
    external scale, since "good price" only means something relative to
    the other quotes for the same part."""
    clean = [v for v in values if v is not None]
    if not clean or max(clean) == min(clean):
        return [0.5 if v is not None else None for v in values]  # no signal to differentiate on
    lo, hi = min(clean), max(clean)
    norm = [(v - lo) / (hi - lo) if v is not None else None for v in values]
    return [(1 - n if n is not None else None) for n in norm] if lower_is_better else norm


def _qualification_score(vendor_status: str, iso9001: str) -> float:
    if vendor_status == "APPROVED_EXISTING":
        return 1.0
    if iso9001 == "Certified":
        return 0.75
    if iso9001 == "Unknown":
        return 0.25  # unqualified until confirmed - not treated as a coin flip
    return 0.0  # explicitly not certified


def build_comparison(candidates: list, weights: dict = None) -> list:
    """candidates: list of dicts, each with at least unit_price, lead_time_days,
    vendor_status, iso9001. Returns the same list with 'score' added to each,
    sorted best-first. Ties and missing data are visible in the output, not
    resolved silently - a human reviewing this sheet should be able to see
    exactly why one candidate scored above another."""
    weights = weights or DEFAULT_WEIGHTS

    price_scores = _normalize([c.get("unit_price") for c in candidates], lower_is_better=True)
    lead_scores = _normalize([c.get("lead_time_days") for c in candidates], lower_is_better=True)

    scored = []
    for c, p_score, l_score in zip(candidates, price_scores, lead_scores):
        q_score = _qualification_score(c.get("vendor_status", ""), c.get("iso9001", ""))
        components = {"price": p_score, "lead_time": l_score, "qualification": q_score}
        # Missing price/lead-time data doesn't get averaged away silently -
        # it drags the score toward 0, which is visible in the sheet as
        # "this candidate is incomplete," not indistinguishable from a
        # genuinely weak quote.
        total = sum(weights[k] * (v if v is not None else 0) for k, v in components.items())
        scored.append({**c, "score": round(total, 3), "score_components": components})

    return sorted(scored, key=lambda x: x["score"], reverse=True)
