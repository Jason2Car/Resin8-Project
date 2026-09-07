# Resin8 Quoting Engine — Prototype

Six stages, run in order, each stage's output feeding the next. Everything
here runs end to end against synthetic data with zero network access; real
operation needs the credentials/APIs noted per stage below.

`example_run/` holds one committed sample run's output at every stage, so
you can inspect what this produces without running anything first.

## Setup

```
pip install -r requirements.txt          # only openpyxl + pandas are required to run the structural logic
                                          # anthropic / requests / playwright are for the real (non-mocked) backends - see per-stage notes below
playwright install chromium              # only if you're wiring up real portal navigation (Stage 4)
```

## Run order

```
python3 sample_bom.py                                    # generates sample_bom_raw.xlsx (skip once you have a real BOM)
python3 pipeline.py                                       # Stage 1  -> standardized_bom.xlsx
cd part_resolver      && python3 pipeline_stage2.py       # Stage 2  -> resolved_bom.xlsx
cd supplier_discovery && python3 pipeline_stage3.py        # Stage 3  -> sourced_bom.xlsx
cd rfq                && python3 pipeline_stage4.py        # Stage 4  -> rfqs_sent.xlsx, quotes_received.xlsx
cd best_offer          && python3 pipeline_stage5.py        # Stage 5  -> comparison_bom.xlsx
cd final_output        && python3 pipeline_stage6.py        # Stage 6  -> final_quote.xlsx  (the client deliverable)
```

Each stage script expects the previous stage's output file one directory up
(`../standardized_bom.xlsx`, etc.) — copy the file forward, or point the
`run()` calls at wherever you're keeping things.

## Stage 1 — BOM normalization (root directory)
`sample_bom.py`, `header_detect.py`, `classify.py`, `completeness_check.py`, `pipeline.py`

Finds the real header row even if it's not row 1, classifies each column
(header text + sampled content, not just row 2), keeps both an internal and
a manufacturer part-number column if a BOM has both, and flags BOMs that
have motor/electronics lines but no wiring/connector lines at all.
Needs: nothing extra to run the structural logic. `pip install anthropic`
+ `ANTHROPIC_API_KEY` to run the column-disambiguation and reasoning-
consistency LLM checks (`llm.py`) — without it, ambiguous cases are flagged
for review instead of guessed.

## Stage 2 — Part resolution (`part_resolver/`)
`router.py`, `nexar_client.py`, `mechanical_search.py`, `mock_catalog.py`, `resolve.py`, `pipeline_stage2.py`

Routes each line to an electronics path (Octopart/Nexar — real API client
included) or a mechanical path (no equivalent aggregator exists —
`mechanical_search.py` is an honest placeholder, not a stub pretending to
work). Confirms exact-ID matches via a batched LLM plausibility check
rather than trusting a part-number match blindly.
Needs: `NEXAR_CLIENT_ID`/`NEXAR_CLIENT_SECRET` + `pip install requests` for
real electronics lookups. A mechanical search backend still needs to be
chosen and wired in (see the module's docstring for the tradeoffs).

## Stage 3 — Vendor coverage & qualification (`supplier_discovery/`)
`approved_vendors.py`, `qualification.py`, `supplier_search.py`, `supplier_contacts.py`, `pipeline_stage3.py`

Checks each resolved part against the client's existing approved vendor
list. The contact/login lookup is wrapped in try/except so one bad
manufacturer name can't crash the whole batch, and lines with a resolved
manufacturer but no saved email contact or portal login are marked
`UNEXPLORED_SOURCE` — a distinct status from `NEEDS_QUALIFICATION`, since
"we don't know how to reach them yet" is a different problem than "we know
them, they're just not qualified." Stage 4 skips these cleanly instead of
attempting a dispatch with nowhere to send it, and Stage 6's final status
column says so explicitly rather than folding it into a generic failure.
Anything not covered also gets an ISO 9001 check (usually comes back
"Unknown" — there's no unified public registry, this is flagged not
faked).
Needs: a real approved-vendor-list export in place of `approved_vendors.py`'s
mock set, and a real qualification workflow behind `qualification.py`.

## Stage 4 — RFQ dispatch & quote retrieval (`rfq/`)
`rfq_builder.py`, `email_client.py`, `mock_email_backend.py`, `portal_navigator.py`, `mock_portal_backend.py`, `pipeline_stage4.py`

Sends RFQ emails with a reference ID for reply matching, and separately
checks portal-based suppliers directly. Portal navigation reads the page's
actual HTML (via an LLM interpreting the real links/fields) rather than
guessing from a fixed keyword list, and every failure returns *why* and
*where* it stopped (`stage_reached`, page title/URL) so failing layouts can
be spotted as a pattern, not just individually missed.
Needs: `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` + `IMAP_HOST`/`IMAP_USER`/
`IMAP_PASSWORD` for real email; `pip install playwright && playwright install
chromium` + `PORTAL_USERNAME`/`PORTAL_PASSWORD` for real portal checks.

## Stage 5 — Best-offer comparison (`best_offer/`)
`selection.py`, `pipeline_stage5.py`

Scores each line's candidate quote(s) on price, lead time, and
qualification — but the weighting (`DEFAULT_WEIGHTS`) is a plain parameter,
not a baked-in business decision. The output sheet itself is the
supporting evaluation record the brief's neutrality requirement asks for.
Known limitation: Stage 2/3 currently resolve one supplier per line, so
there's usually only one candidate to "compare" — the scoring logic is
written for N candidates once that's addressed upstream.

## Stage 6 — Final output (`final_output/`)
`status.py`, `pipeline_stage6.py`

Joins Stages 1, 3, and 5 into one file, classifies every line as
`FIRM_QUOTE` / `ESTIMATE` / `SUBSTITUTION` / `UNSOURCED`, and never drops a
line — unsourced parts get a row with a reason, not a blank. A line marked
`UNEXPLORED_SOURCE` in Stage 3 lands in the `UNSOURCED` bucket here too
(no quote is possible either way), but the detail column says which one it
actually was — "no supplier found" and "supplier found, but nobody's
reached out to them yet" are different problems and shouldn't read the
same to whoever's reviewing this file. This is the file a client engineer
downloads.

## Browser demo (`quoting_engine_demo.html`)

A standalone, single-file interactive version of Stages 1–6 — no server,
no build step, open it directly in a browser. Drop a `.xlsx` in or click
"Load sample BOM" to watch it move through the pipeline live, with weight
sliders for Stage 5 you can drag in real time.

Stage 1's logic (header detection, column classification, wiring
completeness check) is genuinely reimplemented in JS, tested line-for-line
against the Python version under Node before being embedded, and runs for
real on whatever file you drop in. Stages 2–6 use the same small mocked
catalog/vendor/quote data as the Python prototype (same part numbers, same
manufacturers, same canned replies) — a real backend can't run inside a
static page, so anything outside that mock set correctly shows up as
`NO_MATCH` / `UNSOURCED` rather than a fabricated result. The `UNEXPLORED_SOURCE`
handling added to Stage 3 (see above) is mirrored here too, including the
try/catch around the contact lookup.

## Known gaps, by design not by accident
- One candidate supplier per line (Stage 2/3) — limits Stage 5's comparison.
- Mechanical part search and general supplier discovery have no backend
  wired in (`mechanical_search.py`, `supplier_search.py`) — there's no
  aggregator API for this the way Octopart covers electronics.
- Supplier contact/login capture (`supplier_contacts.py`) is a mock
  directory, not a real onboarding process — Stage 3 now handles a missing
  or broken lookup gracefully (`UNEXPLORED_SOURCE`, try/except), but
  something still has to actually go find and record that contact info
  the first time a new supplier shows up.
- ISO 9001 / broader qualification (labor, export control, insurance) has
  no API answer at all — `qualification.py` always returns "unknown" and
  routes to a human reviewer by design.
- Portal navigation's generic path is best-effort — it fails closed with a
  diagnostic on anything it doesn't recognize, rather than guessing.
- Everything runs sequentially — fine for a handful of lines, needs
  parallelizing (async/thread pool) for real BOM volume under an
  hours-not-weeks turnaround target.
