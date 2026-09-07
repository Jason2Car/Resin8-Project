"""
Exactly what you assumed: this doesn't compute anything new, it joins the
standardized BOM (original line, traceable) with Stage 3's supplier data
and Stage 5's selected quote, adds a status column via status.py, and writes
one Excel file matching the brief's 8-field output spec. Unsourced lines
still get a row, with FAILURE_REASON populated - never a blank/dropped line.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bom_pipeline/

from openpyxl import load_workbook, Workbook
from status import classify

FINAL_COLUMNS = [
    "Source Row", "BOM Name", "BOM Unit ID", "BOM Specifications/Size", "BOM Quantity", "BOM Reasoning",
    "Quoted Part Number", "Supplier", "Supplier Qualification (ISO 9001)",
    "Unit Price", "Extended Price", "Lead Time (days)", "Estimated Ship Date", "Quote Validity",
    "Status", "Status Detail", "Evaluation Record Reference",
]


def run(standardized_path: str, sourced_path: str, comparison_path: str, output_path: str = "final_quote.xlsx"):
    std_rows = {r[5]: {"name": r[0], "unit_id": r[1], "specs": r[2], "qty": r[3], "reasoning": r[4]}
                for r in load_workbook(standardized_path, data_only=True)["Standardized"]
                .iter_rows(min_row=2, values_only=True)}

    sourced_wb = load_workbook(sourced_path, data_only=True)
    sourced_rows = {r[5]: {"resolved_unit_id": r[8], "manufacturer": r[9], "vendor_status": r[11],
                            "iso9001": r[12], "match_confidence": r[7]}
                    for r in sourced_wb["Sourced"].iter_rows(min_row=2, values_only=True)}

    comparison_wb = load_workbook(comparison_path, data_only=True)
    comparison_ws = comparison_wb["Comparison"]
    selected_by_row = {}
    for row in comparison_ws.iter_rows(min_row=3, values_only=True):  # row 1 is the weights note, row 2 is headers
        source_row, manufacturer, vendor_status, iso9001, match_confidence, unit_price, lead_time, score, selected = row
        if selected:
            selected_by_row[source_row] = {"unit_price": unit_price, "lead_time_days": lead_time}

    review_rows = []
    if "Review Needed" in comparison_wb.sheetnames:
        review_rows = [{"Source Row": r[0], "Issue": r[1]}
                        for r in comparison_wb["Review Needed"].iter_rows(min_row=2, values_only=True) if r[0] is not None]

    final_rows = []
    for source_row, bom in std_rows.items():
        sourced = sourced_rows.get(source_row, {})
        selected = selected_by_row.get(source_row, {})

        unit_price = selected.get("unit_price")
        qty = bom["qty"] or 0
        extended_price = round(unit_price * qty, 2) if unit_price is not None else None

        status, detail = classify(sourced.get("vendor_status", "UNSOURCED"),
                                   sourced.get("match_confidence", ""), unit_price)

        final_rows.append({
            "Source Row": source_row, "BOM Name": bom["name"], "BOM Unit ID": bom["unit_id"],
            "BOM Specifications/Size": bom["specs"], "BOM Quantity": bom["qty"], "BOM Reasoning": bom["reasoning"],
            "Quoted Part Number": sourced.get("resolved_unit_id", ""), "Supplier": sourced.get("manufacturer", ""),
            "Supplier Qualification (ISO 9001)": sourced.get("iso9001", ""),
            "Unit Price": unit_price, "Extended Price": extended_price,
            "Lead Time (days)": selected.get("lead_time_days"), "Estimated Ship Date": "", "Quote Validity": "",
            "Status": status, "Status Detail": detail,
            "Evaluation Record Reference": f"comparison_bom.xlsx, Source Row {source_row}",
        })

    _write_output(final_rows, review_rows, output_path)
    return final_rows, review_rows


def _write_output(final_rows, review_rows, output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Final Quote"
    ws.append(FINAL_COLUMNS)
    for r in final_rows:
        ws.append([r[c] for c in FINAL_COLUMNS])

    ws2 = wb.create_sheet("Review Needed")
    ws2.append(["Source Row", "Issue"])
    for r in review_rows:
        ws2.append([r["Source Row"], r["Issue"]])

    wb.save(output_path)


if __name__ == "__main__":
    rows, review = run("../standardized_bom.xlsx", "../sourced_bom.xlsx", "../comparison_bom.xlsx")
    statuses = {}
    for r in rows:
        statuses[r["Status"]] = statuses.get(r["Status"], 0) + 1
    print(statuses)
    print(f"{len(review)} rows in review queue")
