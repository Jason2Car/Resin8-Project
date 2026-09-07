"""
Classifies each column into a canonical role. Two fixes applied after
testing surfaced real problems:

1. Word-boundary matching, not substring. A naive `"item" in header.lower()`
   matched inside "Line Item" (a line-number column, not a description) -
   same bug class the router hit with "ic" inside "acrylic". Every keyword
   check here now requires a word boundary.

2. UNIT_ID is split into UNIT_ID_MFG and UNIT_ID_INTERNAL. The brief is
   explicit that BOMs can carry BOTH an internal "The Client" part number
   AND a manufacturer part number as separate columns. Collapsing both into
   one UNIT_ID role meant pipeline.py would silently keep whichever column
   happened to come first and drop the other - if that dropped column was
   the manufacturer number, Stage 2's catalog lookups break on a part that
   actually had a perfectly good MPN. pipeline.py now prefers UNIT_ID_MFG
   when both are present, and folds the internal number into Reasoning
   instead of discarding it.
"""
import re
import pandas as pd

CANONICAL_TYPES = ["NAME", "UNIT_ID_MFG", "UNIT_ID_INTERNAL", "SPECS", "QUANTITY", "REASONING", "OTHER"]

HEADER_KEYWORDS = {
    "UNIT_ID_MFG":      ["part number", "part no", "p/n", "pn", "mfg part", "mpn",
                          "manufacturer part", "component"],
    "UNIT_ID_INTERNAL": ["internal number", "internal part", "item number"],
    "NAME":             ["description", "desc", "name"],
    "SPECS":            ["spec", "size", "dimension", "rating", "value", "tolerance"],
    "QUANTITY":         ["qty", "quantity", "count"],
    "REASONING":        ["note", "notes", "reason", "comment", "remark"],
    "OTHER":            ["line", "ln", "item", "rev", "revision", "uom", "unit of measure", "manufacturer"],
}

SAMPLE_SIZE = 8  # rows sampled per column before locking a type - not just row 2


def _keyword_match(header_text: str, keywords: list) -> bool:
    # \b...\b alone is too strict - it rejects "Comments" against keyword
    # "comment" (no boundary before the plural "s"). Allow an optional
    # trailing "s" so simple plurals still match, without falling back to
    # unbounded substring matching (which is what caused the original bug).
    return any(re.search(r"\b" + re.escape(k) + r"s?\b", header_text) for k in keywords)


def classify_by_header(header_text: str):
    h = str(header_text).strip().lower()
    for ctype, keywords in HEADER_KEYWORDS.items():
        if _keyword_match(h, keywords):
            return ctype, "strong"
    return None, "none"


def classify_by_content(series: pd.Series):
    sample = series.dropna().astype(str).head(SAMPLE_SIZE).tolist()
    if not sample:
        return None, "none"

    numeric_ratio = sum(1 for v in sample if re.fullmatch(r"-?\d+(\.\d+)?", v.strip())) / len(sample)
    avg_len = sum(len(v) for v in sample) / len(sample)
    has_space_ratio = sum(1 for v in sample if " " in v.strip()) / len(sample)
    alnum_code_ratio = sum(1 for v in sample if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-_/.]{1,20}", v.strip())) / len(sample)

    if numeric_ratio >= 0.75:
        return "QUANTITY", "strong"
    if alnum_code_ratio >= 0.75 and has_space_ratio <= 0.25 and avg_len <= 20:
        return "UNIT_ID_MFG", "medium"  # content alone can't tell mfg vs internal - header must disambiguate that
    if avg_len >= 15 and has_space_ratio >= 0.5:
        return "NAME", "weak"
    return None, "none"


def resolve_column_types(df: pd.DataFrame):
    mapping = {}
    ambiguous = []

    for col in df.columns:
        if col == "_source_row":
            continue

        header_guess, header_conf = classify_by_header(col)
        content_guess, content_conf = classify_by_content(df[col])

        if header_guess and (content_guess is None or content_guess == header_guess
                              or header_guess.startswith("UNIT_ID") and content_guess == "UNIT_ID_MFG"
                              or header_conf == "strong"):
            mapping[col] = header_guess
        elif header_guess is None and content_guess and content_conf == "strong":
            mapping[col] = content_guess
        else:
            ambiguous.append({
                "column": col,
                "header_guess": header_guess,
                "content_guess": content_guess,
                "samples": df[col].dropna().astype(str).head(5).tolist(),
            })

    return mapping, ambiguous


if __name__ == "__main__":
    from header_detect import load_with_detected_header
    _, df = load_with_detected_header("sample_bom_raw.xlsx")
    mapping, ambiguous = resolve_column_types(df)
    print("resolved:", mapping)
    print("ambiguous:", ambiguous)
