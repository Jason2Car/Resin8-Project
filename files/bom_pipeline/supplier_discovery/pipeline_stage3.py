"""
Reads Stage 2's output, adds Vendor Status per line:
  APPROVED_EXISTING  - manufacturer is already on the approved vendor list,
                       nothing further needed for this line
  NEEDS_QUALIFICATION - a manufacturer was resolved (Stage 2 found the part)
                       but it isn't approved yet - ISO 9001 status gets
                       checked (usually comes back unknown - see
                       qualification.py) and flagged for the qualification
                       reviewer, not blocked
  UNSOURCED          - Stage 2 found no part match at all - supplier
                       discovery runs (usually empty in this sandbox - see
                       supplier_search.py) and this is exactly the case the
                       brief means by "every unsourced line explained"

Review queue keeps being carried forward and appended to, same as Stage 2.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bom_pipeline/

from openpyxl import load_workbook, Workbook
from approved_vendors import is_covered
from qualification import check_iso9001
from supplier_search import find_suppliers
from supplier_contacts import get_contact

SOURCED_COLUMNS = ["Name", "Unit ID", "Specifications/Size", "Quantity", "Reasoning",
                    "Source Row", "Category", "Match Confidence", "Resolved Unit ID",
                    "Manufacturer", "Catalog Description", "Vendor Status", "ISO 9001",
                    "Contact Channel", "Contact Email", "Portal URL"]


def run(input_path: str, output_path: str = "sourced_bom.xlsx"):
    wb_in = load_workbook(input_path, data_only=True)
    resolved_ws = wb_in["Resolved"]
    rows = list(resolved_ws.iter_rows(min_row=2, values_only=True))

    review_rows = []
    if "Review Needed" in wb_in.sheetnames:
        review_rows = [{"Source Row": r[0], "Issue": r[1]}
                        for r in wb_in["Review Needed"].iter_rows(min_row=2, values_only=True) if r[0] is not None]

    sourced = []
    for (name, unit_id, specs, qty, reasoning, source_row, category,
         match_confidence, resolved_unit_id, manufacturer, catalog_description) in rows:

        if match_confidence == "NO_MATCH":
            candidates = find_suppliers(name)
            vendor_status = "UNSOURCED"
            iso_status = ""
            if candidates:
                review_rows.append({"Source Row": source_row,
                                     "Issue": f"Candidate supplier(s) found for unmatched line, needs qualification: {candidates}"})
            else:
                review_rows.append({"Source Row": source_row,
                                     "Issue": "No supplier candidates found - needs manual sourcing, no automated path available yet."})
        elif is_covered(manufacturer):
            vendor_status = "APPROVED_EXISTING"
            iso_status = "N/A (pre-approved)"
        else:
            vendor_status = "NEEDS_QUALIFICATION"
            iso = check_iso9001(manufacturer)
            iso_status = "Unknown" if iso is None else ("Certified" if iso else "Not certified")
            review_rows.append({"Source Row": source_row,
                                 "Issue": f"'{manufacturer}' is not yet an approved vendor "
                                          f"(ISO 9001 status: {iso_status}) - needs qualification review before an RFQ can be sent."})

        sourced.append({
            "Name": name, "Unit ID": unit_id, "Specifications/Size": specs, "Quantity": qty,
            "Reasoning": reasoning, "Source Row": source_row, "Category": category,
            "Match Confidence": match_confidence, "Resolved Unit ID": resolved_unit_id,
            "Manufacturer": manufacturer, "Catalog Description": catalog_description,
            "Vendor Status": vendor_status, "ISO 9001": iso_status,
        })

        contact = get_contact(manufacturer) if manufacturer else None
        if manufacturer and vendor_status != "UNSOURCED" and not contact:
            review_rows.append({"Source Row": source_row,
                                 "Issue": f"'{manufacturer}' has no contact/channel on file - "
                                          f"cannot send an RFQ until this is captured during qualification."})
        sourced[-1]["Contact Channel"] = contact["channel"] if contact else ""
        sourced[-1]["Contact Email"] = contact["email"] if contact else ""
        sourced[-1]["Portal URL"] = contact["portal_url"] if contact else ""

    _write_output(sourced, review_rows, output_path)
    return sourced, review_rows


def _write_output(sourced, review_rows, output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sourced"
    ws.append(SOURCED_COLUMNS)
    for r in sourced:
        ws.append([r[c] for c in SOURCED_COLUMNS])

    ws2 = wb.create_sheet("Review Needed")
    ws2.append(["Source Row", "Issue"])
    for r in review_rows:
        ws2.append([r["Source Row"], r["Issue"]])

    wb.save(output_path)


if __name__ == "__main__":
    sourced, review = run("../resolved_bom.xlsx")
    counts = {}
    for r in sourced:
        counts[r["Vendor Status"]] = counts.get(r["Vendor Status"], 0) + 1
    print(counts)
    print(f"{len(review)} rows in review queue")
