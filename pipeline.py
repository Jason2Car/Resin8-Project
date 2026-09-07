"""
End to end: raw messy BOM.xlsx -> standardized_bom.xlsx with two sheets:
  - "Standardized": Name | Unit ID | Specifications/Size | Quantity | Reasoning
    (plus Source Row, so every line traces back to the input - required by
    the brief even though it's not one of your 5 requested columns)
  - "Review Needed": anything the pipeline wasn't confident about, with why.
    This replaces "call the user" - it's a queue they clear in one pass
    instead of the pipeline stopping and waiting on every uncertain line.
"""
import pandas as pd
from openpyxl import Workbook

from header_detect import load_with_detected_header
from classify import resolve_column_types
from llm import disambiguate_columns, check_reasoning_consistency
from completeness_check import check_missing_wiring

OUTPUT_COLUMNS = ["Name", "Unit ID", "Specifications/Size", "Quantity", "Reasoning"]


def run(input_path: str, output_path: str = "standardized_bom.xlsx"):
    header_idx, df = load_with_detected_header(input_path)

    mapping, ambiguous = resolve_column_types(df)

    review_rows = []
    if ambiguous:
        resolved_by_llm = disambiguate_columns(ambiguous)
        for col_info in ambiguous:
            col = col_info["column"]
            if col in resolved_by_llm:
                mapping[col] = resolved_by_llm[col]
            else:
                review_rows.append({
                    "Source Row": "(column-level)",
                    "Issue": f"Could not classify column '{col}' - header and content "
                             f"both ambiguous. Samples: {col_info['samples']}",
                })

    # Find which column (if any) maps to each canonical role.
    role_to_col = {}
    for col, ctype in mapping.items():
        role_to_col.setdefault(ctype, col)  # first match wins if duplicates

    # UNIT_ID: prefer the manufacturer part number column when both an
    # internal and a manufacturer ID column exist - catalog lookups in
    # Stage 2 need the MFG number specifically. The internal number, if
    # present, is kept (folded into Reasoning below) rather than discarded.
    unit_id_col = role_to_col.get("UNIT_ID_MFG") or role_to_col.get("UNIT_ID_INTERNAL")
    internal_id_col = role_to_col.get("UNIT_ID_INTERNAL") if role_to_col.get("UNIT_ID_MFG") else None

    required_cols = {"NAME": role_to_col.get("NAME"), "UNIT_ID": unit_id_col, "QUANTITY": role_to_col.get("QUANTITY")}
    missing_required = [r for r, c in required_cols.items() if c is None]
    if missing_required:
        raise ValueError(
            f"Could not locate required column(s) {missing_required} in the sheet. "
            f"Resolved mapping was: {mapping}"
        )

    standardized = []
    for _, row in df.iterrows():
        name = row.get(role_to_col.get("NAME"), "")
        unit_id = row.get(unit_id_col, "")
        specs = row.get(role_to_col.get("SPECS"), "") if "SPECS" in role_to_col else ""
        qty = row.get(role_to_col.get("QUANTITY"), "")
        reasoning = row.get(role_to_col.get("REASONING"), "") if "REASONING" in role_to_col else ""
        reasoning = "" if pd.isna(reasoning) else str(reasoning).strip()

        if internal_id_col:
            internal_val = row.get(internal_id_col, "")
            if not pd.isna(internal_val) and str(internal_val).strip():
                tag = f"[internal id: {str(internal_val).strip()}]"
                reasoning = f"{reasoning} {tag}".strip() if reasoning else tag

        if (pd.isna(unit_id) or str(unit_id).strip() == "") and (pd.isna(name) or str(name).strip() == ""):
            review_rows.append({
                "Source Row": row["_source_row"],
                "Issue": "No part number AND no description - cannot identify this part at all.",
            })
            continue

        standardized.append({
            "Name": "" if pd.isna(name) else str(name).strip(),
            "Unit ID": "" if pd.isna(unit_id) else str(unit_id).strip(),
            "Specifications/Size": "" if pd.isna(specs) else str(specs).strip(),
            "Quantity": qty,
            "Reasoning": reasoning,
            "_source_row": row["_source_row"],
        })

    # Reasoning consistency check - only rows that have a reasoning value get sent.
    consistency_input = [
        {"source_row": r["_source_row"], "name": r["Name"], "unit_id": r["Unit ID"],
         "quantity": r["Quantity"], "reasoning": r["Reasoning"]}
        for r in standardized if r["Reasoning"]
    ]
    consistency_results = check_reasoning_consistency(consistency_input)

    for r in standardized:
        result = consistency_results.get(r["_source_row"])
        if result is None and r["Reasoning"]:
            # Had reasoning to check but no LLM available/no network in this
            # environment - flag rather than silently skip the check.
            review_rows.append({
                "Source Row": r["_source_row"],
                "Issue": "Has reasoning/notes text but consistency check could not run "
                         "(no LLM access) - needs manual read-through.",
            })
        elif result and not result["consistent"]:
            review_rows.append({
                "Source Row": r["_source_row"],
                "Issue": f"Reasoning may not match name/quantity: {result['note']}",
            })

    wiring_note = check_missing_wiring([r["Name"] for r in standardized])
    if wiring_note:
        review_rows.append({"Source Row": "(BOM-level)", "Issue": wiring_note})

    _write_output(standardized, review_rows, output_path)
    return standardized, review_rows


def _write_output(standardized, review_rows, output_path):
    wb = Workbook()

    ws = wb.active
    ws.title = "Standardized"
    ws.append(OUTPUT_COLUMNS + ["Source Row"])
    for r in standardized:
        ws.append([r["Name"], r["Unit ID"], r["Specifications/Size"],
                    r["Quantity"], r["Reasoning"], r["_source_row"]])

    ws2 = wb.create_sheet("Review Needed")
    ws2.append(["Source Row", "Issue"])
    for r in review_rows:
        ws2.append([r["Source Row"], r["Issue"]])

    wb.save(output_path)


if __name__ == "__main__":
    standardized, review = run("sample_bom_raw.xlsx")
    print(f"{len(standardized)} lines standardized, {len(review)} flagged for review")
