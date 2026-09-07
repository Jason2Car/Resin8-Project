"""
Canned responses standing in for what Nexar/a mechanical search backend
would actually return. Only used when the real clients return nothing
(no credentials/network) AND this module is explicitly wired in - see
pipeline_stage2.py's `use_mock` flag. Never falls back to this silently in
a real run; it exists purely so the resolution logic is checkable here.
"""

EXACT_BY_ID = {
    "TB-100": {"manufacturer": "ElectroConn", "description": "10-position screw terminal block, 300V rated", "mpn": "TB-100", "buy_url": "https://www.electroconn-example.com/products/TB-100"},
    "PSU-24-5A": {"manufacturer": "MeanTech", "description": "24V 5A enclosed switching power supply", "mpn": "PSU-24-5A", "buy_url": "https://www.meantech-example.com/shop/PSU-24-5A"},
    "8420-K": {"manufacturer": "FastenCo", "description": "Hex socket cap screw, M4 x 12mm, stainless", "mpn": "8420-K"},
    "LM-6UU": {"manufacturer": "LinearMotion Inc", "description": "Linear ball bearing, 6mm bore", "mpn": "LM6UU"},
}

DESCRIPTION_SEARCH_RESULTS = {
    "servo motor bracket": [
        {"manufacturer": "McMaster-Carr", "description": "Aluminum mounting bracket for NEMA 17 servo motors", "mpn": "1234K56"},
    ],
    "right angle gearbox, 20:1 ratio": [
        {"manufacturer": "AndyMark", "description": "Right angle planetary gearbox, 20:1 ratio", "mpn": "am-3103a"},
    ],
}


def lookup_by_mpn(mpn: str):
    return EXACT_BY_ID.get(mpn.strip())


def search_by_description(description: str, limit: int = 3):
    key = description.strip().lower()
    return DESCRIPTION_SEARCH_RESULTS.get(key, [])[:limit]
