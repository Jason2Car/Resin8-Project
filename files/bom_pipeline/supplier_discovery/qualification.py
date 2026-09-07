"""
Same shape of gap as mechanical_search.py: there is no single API that
answers "is this supplier ISO 9001 certified." IAF-recognized certification
bodies each keep their own registries, coverage is inconsistent, and most
of the brief's fuller policy (labor, export control, insurance, cyber,
financial) has no API answer at all - it's request-the-documents-and-review,
which is exactly why the brief says that policy "is still being confirmed."

Realistic automation ceiling: check what's publicly checkable (a certificate
number against its issuing body's registry, when the supplier provides one),
and route everything else - which will be most of it - to a human
qualification reviewer as part of onboarding a new supplier, not as a
one-off block per BOM line.

No backend wired in here on purpose - see pipeline_stage3.py, this always
returns None (unknown) and callers must treat that as "needs qualification
review," never as "assume compliant."
"""


def check_iso9001(manufacturer: str):
    """Returns True/False if verifiable, or None if unknown - which is the
    expected result until a real registry lookup or document-review
    workflow is wired in."""
    return None
