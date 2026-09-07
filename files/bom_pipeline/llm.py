"""
Two LLM-backed steps, both intentionally BATCHED rather than one-call-per-row:
with a few hundred BOM lines and an hours-not-weeks target, one call per row
is both slow and needlessly expensive.

  1. disambiguate_columns(): only called for columns classify.py couldn't
     resolve on its own. One call covers every ambiguous column in the sheet.
  2. check_reasoning_consistency(): only called for rows that actually have a
     reasoning/notes value. Batches ~25 rows per call.

This is written against the real Anthropic API (anthropic Python SDK) so it
runs as-is once you add an ANTHROPIC_API_KEY and have network access. In this
sandbox neither is available, so both functions fail closed: no API key ->
return None / empty, and the pipeline treats that exactly like "the LLM was
unsure" - it flags for human review rather than guessing or crashing.
"""
import json
import os

MODEL = "claude-sonnet-4-6"


def _client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        return anthropic.Anthropic()
    except ImportError:
        return None


def disambiguate_columns(ambiguous_cols: list) -> dict:
    """ambiguous_cols: list of {column, header_guess, content_guess, samples}
    Returns {column_name: canonical_type}, only for columns it's confident about.
    Unresolved columns are simply absent from the result - pipeline.py flags
    those for human mapping."""
    client = _client()
    if client is None or not ambiguous_cols:
        return {}

    prompt = (
        "You are classifying spreadsheet columns from a bill of materials into "
        "one of: NAME, UNIT_ID, SPECS, QUANTITY, REASONING, OTHER.\n"
        "NAME = part description. UNIT_ID = part/manufacturer number. "
        "SPECS = size/rating/spec value. QUANTITY = numeric qty. "
        "REASONING = free-text notes/justification. OTHER = anything else "
        "(line number, revision, unit of measure, manufacturer name alone).\n\n"
        f"Columns:\n{json.dumps(ambiguous_cols, indent=2)}\n\n"
        "Respond with ONLY a JSON object mapping column name to type. "
        "Omit any column you are not reasonably confident about."
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def check_part_plausibility(candidates: list, batch_size: int = 25) -> dict:
    """candidates: list of {source_row, bom_name, catalog_description}
    Returns {source_row: {"plausible": bool, "note": str}}. Only called for
    lines where an exact unit-id match was found in a catalog - this decides
    whether that catalog hit is actually the same part as the BOM line
    describes, or a coincidental ID match / likely wrong part number typed
    into the source BOM."""
    client = _client()
    if client is None or not candidates:
        return {}

    results = {}
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        prompt = (
            "For each line, a BOM part name and the description of the catalog part "
            "found under that same part number are given. Decide whether they plausibly "
            "describe the SAME physical part (allow for abbreviation/terse BOM wording), "
            "or whether they clearly don't match (likely a wrong part number in the BOM).\n\n"
            f"{json.dumps(batch, indent=2)}\n\n"
            'Respond with ONLY a JSON array: '
            '[{"source_row": <int>, "plausible": <bool>, "note": "<short reason>"}]'
        )
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        try:
            for item in json.loads(text):
                results[item["source_row"]] = {
                    "plausible": item["plausible"],
                    "note": item.get("note", ""),
                }
        except (json.JSONDecodeError, KeyError):
            continue

    return results


def choose_login_fields(form_fields: list):
    """form_fields: [{"name", "id", "type", "placeholder"}, ...] scraped from
    the actual page's <input> elements. Returns {"username_selector",
    "password_selector"} built from whichever field the model judges most
    likely, or None if nothing looks like a login form at all (e.g. already
    logged in, or this isn't a login page)."""
    client = _client()
    if client is None or not form_fields:
        return None

    prompt = (
        "These are the <input> elements found on a webpage. Identify which one "
        "(if any) is a username/email login field, and which is a password field.\n\n"
        f"{json.dumps(form_fields, indent=2)}\n\n"
        'Respond with ONLY JSON: {"username_index": <int|null>, "password_index": <int|null>} '
        "using the 0-based index into the list above, or null if no such field exists."
    )
    resp = client.messages.create(model=MODEL, max_tokens=200, messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        result = json.loads(text)
        if result.get("username_index") is None or result.get("password_index") is None:
            return None
        u, p = form_fields[result["username_index"]], form_fields[result["password_index"]]
        return {
            "username_selector": f"#{u['id']}" if u.get("id") else f"[name={u.get('name')}]",
            "password_selector": f"#{p['id']}" if p.get("id") else f"[name={p.get('name')}]",
        }
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None


def choose_quote_link(links: list):
    """links: [{"text", "href"}, ...] scraped from the actual page's <a>
    elements. Returns the href most likely to lead to quotes/RFQ status/order
    history, or None if nothing on the page looks relevant."""
    client = _client()
    if client is None or not links:
        return None

    prompt = (
        "These are the links found on a supplier portal webpage after logging in. "
        "Identify which link (if any) most likely leads to viewing quotes, RFQ status, "
        "or order/pricing history for this account.\n\n"
        f"{json.dumps(links, indent=2)}\n\n"
        'Respond with ONLY JSON: {"link_index": <int|null>} using the 0-based index, '
        "or null if none of these links look relevant."
    )
    resp = client.messages.create(model=MODEL, max_tokens=200, messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        result = json.loads(text)
        if result.get("link_index") is None:
            return None
        return links[result["link_index"]]["href"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None


def extract_quote_fields(replies: list, batch_size: int = 15) -> dict:
    """replies: list of {reference_id, body_text}
    Returns {reference_id: {unit_price, extended_price, lead_time_days,
    ship_date, quote_validity, currency, notes}}. Fields the model can't
    find in the text are left as null - never guessed. Batched like the
    other LLM steps; called from a periodic inbox-check job, not per-reply
    in real time, so batching is free."""
    client = _client()
    if client is None or not replies:
        return {}

    results = {}
    for i in range(0, len(replies), batch_size):
        batch = replies[i:i + batch_size]
        prompt = (
            "Extract quote details from each supplier reply below. For each, return "
            "unit_price, extended_price, currency, lead_time_days, ship_date, "
            "quote_validity (the date or period the quote is valid until), and notes "
            "(anything unusual - partial quote, substitution offered, MOQ not met, etc). "
            "Use null for any field not present in the text - never estimate or guess a value.\n\n"
            f"{json.dumps(batch, indent=2)}\n\n"
            'Respond with ONLY a JSON array: '
            '[{"reference_id": "<id>", "unit_price": <num|null>, "extended_price": <num|null>, '
            '"currency": "<str|null>", "lead_time_days": <num|null>, "ship_date": "<str|null>", '
            '"quote_validity": "<str|null>", "notes": "<str>"}]'
        )
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        try:
            for item in json.loads(text):
                results[item["reference_id"]] = item
        except (json.JSONDecodeError, KeyError):
            continue

    return results


def check_reasoning_consistency(rows: list, batch_size: int = 25) -> dict:
    """rows: list of {source_row, name, unit_id, quantity, reasoning}
    Returns {source_row: {"consistent": bool, "note": str}} for rows that had
    a reasoning value. Rows with no reasoning aren't sent - nothing to check."""
    client = _client()
    checkable = [r for r in rows if r.get("reasoning")]
    if client is None or not checkable:
        return {}

    results = {}
    for i in range(0, len(checkable), batch_size):
        batch = checkable[i:i + batch_size]
        prompt = (
            "For each BOM line below, decide whether the reasoning/notes text "
            "is CONSISTENT with the part name and quantity, or whether it "
            "flags a real discrepancy (e.g. notes describe a part the name "
            "doesn't match, or question the quantity).\n\n"
            f"{json.dumps(batch, indent=2)}\n\n"
            'Respond with ONLY a JSON array: '
            '[{"source_row": <int>, "consistent": <bool>, "note": "<short reason>"}]'
        )
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        try:
            for item in json.loads(text):
                results[item["source_row"]] = {
                    "consistent": item["consistent"],
                    "note": item.get("note", ""),
                }
        except (json.JSONDecodeError, KeyError):
            continue  # falls through to "needs review" in pipeline.py

    return results
