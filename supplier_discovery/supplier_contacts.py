"""
This belongs in Stage 3, not Stage 4 - realized while building Stage 4 that
you can't send an RFQ, or even know HOW to reach a supplier, using only a
manufacturer name. Qualification/onboarding is exactly the point where a
real system would capture:
  - an email contact, if the supplier takes RFQs by email
  - a portal URL, if quotes/orders go through their own website
  - which channel to actually use (some suppliers offer both)

Real source: captured during supplier onboarding/qualification (a person
reaches out once, records how this supplier wants to be engaged, and it's
reused for every future line). Mocked here as a small directory.

CHANNEL is deliberately explicit rather than inferred - guessing a channel
from whether an email or portal URL happens to be present is a way to
silently pick wrong when a supplier has both.
"""

# manufacturer -> {channel, email, portal_url}
SUPPLIER_DIRECTORY = {
    "FastenCo":         {"channel": "EMAIL",  "email": "sales@fastenco-example.com",  "portal_url": None},
    "McMaster-Carr":     {"channel": "EMAIL",  "email": "quotes@mcmaster-example.com", "portal_url": None},
    "AndyMark":          {"channel": "EMAIL",  "email": "sales@andymark-example.com",  "portal_url": None},
    "LinearMotion Inc":  {"channel": "PORTAL", "email": None, "portal_url": "https://portal.linearmotion-example.com/rfq"},
}


def get_contact(manufacturer: str):
    """Returns {channel, email, portal_url} or None if this supplier hasn't
    been onboarded yet - which is the expected result for anything Stage 2/3
    just discovered for the first time, not an error."""
    return SUPPLIER_DIRECTORY.get(manufacturer)
