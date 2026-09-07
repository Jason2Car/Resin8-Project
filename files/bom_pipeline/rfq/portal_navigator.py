"""
Two changes from the first version:

1. Finding "where to go" now actually reads the page's real HTML - the
   <input> elements and <a> links are pulled from the live DOM and handed to
   an LLM to interpret (llm.choose_login_fields / choose_quote_link), rather
   than guessing from a fixed list of common field names and link labels.
   That fixed-list guess is kept ONLY as a last-resort fallback for when no
   LLM is available - it's weaker (it can't recognize a login field named
   "acct_id" or a link labeled "Order History"), which is exactly why it's
   not the primary path anymore.

2. Every call returns a structured result, not a bare None. Which stage it
   reached, what the page title/URL were, and why it stopped are all
   recorded - the point of this is so failures are diagnosable in bulk
   later ("half our failed portals are stuck at 'login_fields_not_found',
   probably a shared platform we could special-case"), not just individually
   invisible.

Needs `pip install playwright && playwright install chromium` and network
access, neither available in this sandbox.
"""
import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bom_pipeline/
from llm import choose_login_fields, choose_quote_link

# Per-supplier overrides for portals worth hand-integrating - selectors
# known in advance because someone has actually looked at that specific site.
PORTAL_SCRIPTS = {
    # "https://portal.example-supplier.com/rfq": {
    #     "login_selector": "#username", "password_selector": "#password",
    #     "submit_selector": "button[type=submit]", "quote_link_href": "/my-quotes",
    # },
}

GENERIC_LOGIN_GUESSES = ["input[name=username]", "input[name=email]", "#username", "#email"]
GENERIC_PASSWORD_GUESSES = ["input[name=password]", "#password", "input[type=password]"]
GENERIC_LINK_TEXT_GUESSES = ["quote", "quotes", "rfq", "rfq status", "my orders", "order status"]


def _result(text=None, stage_reached="", page=None, failure_detail=""):
    r = {"text": text, "stage_reached": stage_reached, "failure_detail": failure_detail,
         "page_title": None, "page_url": None}
    if page is not None:
        try:
            r["page_title"] = page.title()
            r["page_url"] = page.url
        except Exception:
            pass
    return r


def fetch_portal_quote(portal_url: str, username: str = None, password: str = None) -> dict:
    """Returns a result dict with keys: text, stage_reached, failure_detail,
    page_title, page_url. `text` is the page's visible text if a quote page
    was found, else None - `stage_reached` and `failure_detail` say why.
    Callers should log the whole dict on failure, not just check `text`."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _result(stage_reached="playwright_not_installed",
                        failure_detail="playwright is not installed in this environment")

    if not username or not password:
        return _result(stage_reached="no_credentials",
                        failure_detail="no username/password provided for this portal")

    script = PORTAL_SCRIPTS.get(portal_url)
    domain = urlparse(portal_url).netloc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(portal_url, timeout=15000)
        except Exception as e:
            browser.close()
            return _result(stage_reached="page_load_failed", failure_detail=f"{domain}: {e}")

        if script:
            try:
                page.fill(script["login_selector"], username)
                page.fill(script["password_selector"], password)
                page.click(script["submit_selector"])
                page.wait_for_load_state("networkidle")
                page.goto(script["quote_link_href"])
                text = page.inner_text("body")
                result = _result(text=text, stage_reached="quote_page_reached_via_script", page=page)
                browser.close()
                return result
            except Exception as e:
                result = _result(stage_reached="hardcoded_script_failed", page=page, failure_detail=str(e))
                browser.close()
                return result

        # Generic path: read the real page structure, then ask an LLM to
        # interpret it, falling back to fixed guesses only if that's
        # unavailable.
        try:
            fields = page.eval_on_selector_all(
                "input",
                "els => els.map(e => ({name: e.name, id: e.id, type: e.type, placeholder: e.placeholder}))",
            )
        except Exception as e:
            browser.close()
            return _result(stage_reached="dom_read_failed", page=page, failure_detail=str(e))

        login_fields = choose_login_fields(fields)
        try:
            if login_fields:
                page.fill(login_fields["username_selector"], username)
                page.fill(login_fields["password_selector"], password)
            else:
                filled = False
                for sel in GENERIC_LOGIN_GUESSES:
                    if page.locator(sel).count() > 0:
                        page.fill(sel, username)
                        filled = True
                        break
                for sel in GENERIC_PASSWORD_GUESSES:
                    if page.locator(sel).count() > 0:
                        page.fill(sel, password)
                        break
                if not filled:
                    result = _result(stage_reached="login_fields_not_found", page=page,
                                     failure_detail="no recognizable username field, with or without LLM assistance")
                    browser.close()
                    return result

            submit = page.locator("button[type=submit]")
            if submit.count() > 0:
                submit.first.click()
                page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            result = _result(stage_reached="login_submit_failed", page=page, failure_detail=str(e))
            browser.close()
            return result

        try:
            links = page.eval_on_selector_all(
                "a", "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))"
            )
        except Exception as e:
            browser.close()
            return _result(stage_reached="dom_read_failed_post_login", page=page, failure_detail=str(e))

        target_href = choose_quote_link([l for l in links if l["text"]])
        if not target_href:
            for label in GENERIC_LINK_TEXT_GUESSES:
                match = [l for l in links if label in l["text"].lower()]
                if match:
                    target_href = match[0]["href"]
                    break

        if not target_href:
            result = _result(stage_reached="quote_link_not_found", page=page,
                             failure_detail=f"landed on '{page.title()}' post-login, no link matched "
                                            f"quotes/RFQ/orders, with or without LLM assistance")
            browser.close()
            return result

        try:
            page.goto(target_href, timeout=10000)
            text = page.inner_text("body")
            result = _result(text=text, stage_reached="quote_page_reached_generic", page=page)
        except Exception as e:
            result = _result(stage_reached="quote_page_load_failed", page=page, failure_detail=str(e))
        browser.close()
        return result
