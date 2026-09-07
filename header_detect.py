"""
The brief is explicit: "a header row that may not start on row 1." So step
zero is finding it, before any column classification can happen.

Approach: read the sheet with no header assumption at all (every cell as a
raw value), score each of the first N rows on how header-like it looks, and
take the best-scoring row. A header row looks like: mostly non-empty, mostly
short strings (not long sentences, not lone numbers), and ideally contains at
least one keyword we recognize from the brief's list of expected variations.
"""
import pandas as pd

KNOWN_HEADER_KEYWORDS = [
    "line", "ln", "item",
    "part", "p/n", "pn", "mfg", "manufacturer",
    "desc", "description",
    "spec", "size", "rating", "value",
    "qty", "quantity", "count",
    "note", "notes", "comment", "reason",
    "rev", "revision", "uom", "unit",
]


def _row_score(cells):
    non_empty = [c for c in cells if c is not None and str(c).strip() != ""]
    if not non_empty:
        return -1.0

    fill_ratio = len(non_empty) / len(cells)

    short_string_count = 0
    keyword_hits = 0
    for c in non_empty:
        s = str(c).strip().lower()
        if len(s) <= 40 and not s.replace(".", "", 1).isdigit():
            short_string_count += 1
        if any(k in s for k in KNOWN_HEADER_KEYWORDS):
            keyword_hits += 1

    short_ratio = short_string_count / len(non_empty)
    keyword_ratio = keyword_hits / len(non_empty)

    # Weighted: keyword match is the strongest signal, then "looks like a
    # label not a number/sentence", then simply not being a mostly-blank row.
    return (keyword_ratio * 3.0) + (short_ratio * 1.5) + (fill_ratio * 1.0)


def find_header_row(raw_df: pd.DataFrame, scan_rows: int = 15) -> int:
    """raw_df must be read with header=None so row 0 is real row 1 of the sheet.
    Returns the integer index (0-based, into raw_df) of the best header-row candidate."""
    best_idx, best_score = 0, -1.0
    for i in range(min(scan_rows, len(raw_df))):
        score = _row_score(raw_df.iloc[i].tolist())
        if score > best_score:
            best_idx, best_score = i, score
    return best_idx


def load_with_detected_header(path: str, sheet_name=0):
    """Returns (header_row_index, dataframe) where dataframe has the detected
    header applied and only the data rows below it."""
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header_idx = find_header_row(raw)

    headers = raw.iloc[header_idx].tolist()
    data = raw.iloc[header_idx + 1:].reset_index(drop=True)
    data.columns = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(headers)]

    # Original row number in the source file, 1-indexed, for traceability
    # back to the input row (the brief requires every output line traces
    # back to its BOM line).
    data["_source_row"] = range(header_idx + 2, header_idx + 2 + len(data))

    return header_idx, data


if __name__ == "__main__":
    idx, df = load_with_detected_header("sample_bom_raw.xlsx")
    print(f"detected header at row {idx + 1} (1-indexed)")
    print(df)
