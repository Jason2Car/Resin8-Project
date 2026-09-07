"""
This is deliberately a different question from Stage 2's catalog match.
Stage 2 asks "does this part exist and who makes it" (Octopart/McMaster/etc,
anyone's catalog). This asks "is that specific manufacturer/supplier already
on THE CLIENT's approved vendor list" - the brief's actual coverage problem:
their German supply chain doesn't cover the American parts they now need,
so most manufacturers Stage 2 resolves to will legitimately NOT be covered
yet, and that's the expected, not the exceptional, case.

Real source: an export from the client's ERP/vendor master, refreshed
periodically. Mocked here as a small in-memory set standing in for that file.
"""

# Stand-in for "The Client"'s approved vendor list export.
APPROVED_VENDORS = {
    "FastenCo",
    "LinearMotion Inc",
}


def is_covered(manufacturer: str) -> bool:
    return manufacturer.strip() in APPROVED_VENDORS if manufacturer else False
