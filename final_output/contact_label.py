"""
One line, one "how do you actually get this" answer - with the type
labeled so the final table is scannable without opening every cell to see
what kind of value it holds. Priority, most to least direct:

  LINK   - a distributor purchase URL (Stage 2, electronics only today) -
           the most transactable thing there is: click it, buy it, done.
  PORTAL - a supplier portal login (Stage 3) - one login away from a quote
           or order, per portal_navigator.py's best-effort automation.
  EMAIL  - a plain contact address (Stage 3) - requires sending an RFQ and
           waiting on a reply.
  NONE   - nothing on file at all - Stage 3 already flagged this as
           UNEXPLORED_SOURCE or UNSOURCED; this just reflects that here too.
"""


def label_contact(purchase_url: str, portal_url: str, contact_email: str) -> tuple:
    """Returns (contact_type, contact_value)."""
    if purchase_url:
        return "LINK", purchase_url
    if portal_url:
        return "PORTAL", portal_url
    if contact_email:
        return "EMAIL", contact_email
    return "NONE", ""
