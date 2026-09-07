"""Canned replies keyed by reference ID, mimicking what fetch_replies()
would return from a real inbox. Only used when pipeline_stage4.py is run
with use_mock=True."""

MOCK_REPLIES = {
    "RESIN8-RFQ-0004": {  # bracket, McMaster-Carr
        "from": "quotes@mcmaster-example.com",
        "subject": "RE: RFQ RESIN8-RFQ-0004 - Servo motor bracket",
        "body": (
            "Thanks for reaching out. For part 1234K56 (Aluminum mounting bracket for "
            "NEMA 17 servo motors), qty 4: unit price $8.75, extended price $35.00. "
            "In stock, ships in 2 business days. Quote valid 30 days from today."
        ),
        "attachments": [],
    },
    "RESIN8-RFQ-0006": {  # gearbox, AndyMark
        "from": "sales@andymark-example.com",
        "subject": "RE: RFQ RESIN8-RFQ-0006 - Right angle gearbox, 20:1 ratio",
        "body": (
            "We can supply the am-3103a gearbox. Note: minimum order quantity is 5 units, "
            "your request was for 2 - happy to quote at 5 if that works. Unit price at MOQ "
            "$42.00, extended $210.00. Lead time 3 weeks, estimated ship 2026-09-27."
        ),
        "attachments": [],
    },
}
