"""
Generates a deliberately messy sample BOM so header_detect/classify/pipeline
can be tested against something that looks like the real thing:
  - junk rows above the real header
  - non-standard column names
  - a blank part number with only a description to go on
  - a notes column that's mostly empty
  - one row where the notes contradict the quantity (for the LLM check to catch)
"""
import openpyxl
from openpyxl import Workbook


def build_sample(path="sample_bom_raw.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "BOM"

    # Row 1-2: junk the header-detector needs to skip past
    ws.append(["Client Corp - Export from ERP", None, None, None, None, None])
    ws.append(["Generated 2026-09-01", None, None, None, None, None])

    # Row 3: the real header, non-standard names on purpose
    ws.append(["Ln", "Mfg P/N", "Desc", "Spec", "Qty per unit", "Comments"])

    # Data rows
    rows = [
        [1, "RS-2210-B", "Servo motor bracket", "Aluminum, 6061-T6",  4, ""],
        [2, "8420-K",    "Hex socket cap screw", "M4 x 12mm",        16, ""],
        [3, "",           "Right angle gearbox, 20:1 ratio", "20:1", 2, "no mfg PN provided by client, matched from description"],
        [4, "TB-100",    "Terminal block", "10 position, 300V",      3, ""],
        [5, "LM-6UU",    "Linear bearing", "6mm bore",                8, "qty looks high for a single-arm design, double-check"],
        [6, "PSU-24-5A", "Power supply",   "24V 5A",                  1, ""],
        [7, "",          "Custom laser-cut acrylic enclosure panel", "3mm thickness", 2,
         "one-off custom part for this design, no standard catalog match expected"],
    ]
    for r in rows:
        ws.append(r)

    wb.save(path)
    return path


if __name__ == "__main__":
    p = build_sample()
    print(f"wrote {p}")
