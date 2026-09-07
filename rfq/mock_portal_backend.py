"""Canned portal page text keyed by manufacturer, mimicking what
fetch_portal_quote_text() would return after a real login + navigation.
Only used when pipeline_stage4.py is run with use_mock=True."""

MOCK_PORTAL_PAGES = {
    "LinearMotion Inc": (
        "My Account > Quotes\n\n"
        "Quote #Q-88213 - LM6UU Linear ball bearing, 6mm bore\n"
        "Quantity: 8   Unit price: $3.10   Extended: $24.80\n"
        "Availability: In stock   Ships: same day if ordered before 2pm\n"
        "This quote is valid through 2026-10-15."
    ),
}
