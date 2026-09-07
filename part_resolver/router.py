"""
There is no unified "look up any part" API. Electronics have one good
aggregator (Octopart/Nexar). Mechanical/hardware parts (brackets, bearings,
fasteners, gearboxes) don't - McMaster-Carr and Grainger offer punchout/EDI
catalogs for procurement systems, not a simple REST lookup, so mechanical
lines get a weaker, search-based resolution path with lower confidence
ceilings by design, not by bug.

This is a cheap keyword router. Ambiguous lines (e.g. "servo motor" - is the
part itself electronic or is this row describing a mechanical bracket for
one?) fall through to MECHANICAL as the safer default, since the mechanical
path's fallback is a broader search rather than a wrong-catalog exact lookup.
"""

ELECTRONIC_KEYWORDS = [
    "resistor", "capacitor", "diode", "transistor", "ic ", "connector",
    "pcb", "relay", "sensor", "microcontroller", "power supply", "psu",
    "terminal", "fuse", "cable", "wire", "battery", "led", "switch",
]

MECHANICAL_KEYWORDS = [
    "screw", "bolt", "nut", "washer", "bracket", "bearing", "gearbox",
    "shaft", "coupling", "enclosure", "panel", "frame", "plate", "gasket",
    "o-ring", "spring", "housing", "mount",
]


import re


def _matches_any(text: str, keywords: list) -> bool:
    # Word-boundary matching, not substring - "ic " as a naive substring
    # matches inside "acrylic enclosure", which is exactly the kind of
    # false positive that silently sent a mechanical part down the wrong
    # catalog path in testing. An optional trailing "s" handles plurals
    # ("resistors", "connectors") without reopening that substring hole.
    return any(re.search(r"\b" + re.escape(k.strip()) + r"s?\b", text) for k in keywords)


def classify_line(name: str, specs: str = "") -> str:
    text = f"{name} {specs}".lower()
    if _matches_any(text, ELECTRONIC_KEYWORDS):
        return "ELECTRONIC"
    if _matches_any(text, MECHANICAL_KEYWORDS):
        return "MECHANICAL"
    return "MECHANICAL"  # safer default - see module docstring
