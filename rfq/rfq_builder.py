"""
One RFQ per (line, supplier). The reference ID is the only thing tying a
future reply back to the right BOM line - it goes in the subject, and
suppliers are asked to keep it there when they reply, since that's the
cheapest way to make matching robust (email threading breaks across
mail clients, forwards, and reply-alls; a plain-text token in the subject
survives all of that).

Known limitation carried over from Stage 2/3: those stages currently
resolve ONE candidate supplier per line. The brief's neutrality requirement
("the quote returned must be the best option found") really wants RFQs out
to multiple suppliers per line so there's something to compare - that's a
Stage 2/3 data-model change (return top-N candidates, not just top-1), not
something Stage 4 can fix on its own. Flagging it here since it's the next
thing worth revisiting.
"""


def reference_id(source_row: int) -> str:
    return f"RESIN8-RFQ-{source_row:04d}"


def build_rfq(name: str, unit_id: str, specs: str, quantity, source_row: int) -> dict:
    ref = reference_id(source_row)
    subject = f"RFQ {ref} - {name}"
    body = (
        f"Requesting a quote for the following part:\n\n"
        f"  Part number: {unit_id or '(none provided - see description)'}\n"
        f"  Description: {name}\n"
        f"  Specification: {specs or 'n/a'}\n"
        f"  Quantity: {quantity}\n\n"
        f"Please include unit price, extended price, lead time, and quote validity period.\n\n"
        f"Reference: {ref}\n"
        f"Please keep this reference in the subject line of your reply so it routes correctly."
    )
    return {"reference_id": ref, "subject": subject, "body": body}
