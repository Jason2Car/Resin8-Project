"""
A different kind of gap than anything Stage 1 checked before: not "this row
is ambiguous" but "an entire expected category of line seems to be missing
from the file." BOMs commonly omit wiring/connector/fastener hardware
either because it's covered by a separate harness drawing, or because it
was just missed in the export - either way, if the BOM has motors, PCBs, or
terminal blocks but not a single wire/cable/connector line, that's worth a
human glancing at before the file is treated as complete.

This is a heuristic reminder, not a hard rule - plenty of legitimate BOMs
really don't need wiring (e.g. pure structural assemblies). It goes into
Review Needed as a BOM-level note, not a per-row block.
"""

IMPLIES_WIRING = ["motor", "servo", "pcb", "sensor", "relay", "power supply",
                   "solenoid", "actuator"]
WIRING_CATEGORY = ["wire", "cable", "wiring harness", "harness", "connector",
                    "terminal", "conduit"]


def check_missing_wiring(names: list) -> str | None:
    text = " ".join(n.lower() for n in names if n)
    has_wiring_trigger = any(k in text for k in IMPLIES_WIRING)
    has_wiring_line = any(k in text for k in WIRING_CATEGORY)

    if has_wiring_trigger and not has_wiring_line:
        return ("This BOM includes motors/electronics/terminal blocks but no wire, cable, "
                "or connector line items were found. Confirm these weren't dropped from the "
                "export (e.g. covered by a separate harness drawing) before treating the BOM as complete.")
    return None
