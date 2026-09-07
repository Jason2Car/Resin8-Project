"""
Uses smtplib/imaplib (stdlib, no extra install) rather than a specific
provider SDK, so this works against any mailbox that exposes SMTP/IMAP -
a dedicated procurement inbox is the realistic setup, not a personal inbox.

Both functions fail closed without credentials/network, same pattern as
nexar_client.py: return None/[] rather than raising, so the pipeline flags
"couldn't send" / "couldn't check" for manual handling instead of crashing
a whole batch over one connectivity issue.
"""
import os
import re
import smtplib
import imaplib
import email as email_lib
from email.mime.text import MIMEText


def send_email(to_addr: str, subject: str, body: str) -> bool:
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_addr = os.environ.get("RFQ_FROM_ADDRESS", user)
    if not all([host, user, password, to_addr]):
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
    return True


def fetch_replies(reference_ids: list) -> dict:
    """Returns {reference_id: {"from": str, "subject": str, "body": str,
    "attachments": [(filename, bytes), ...]}} for any reference ID found in
    an unread inbox subject line. Empty dict if no IMAP access configured."""
    host = os.environ.get("IMAP_HOST")
    user = os.environ.get("IMAP_USER")
    password = os.environ.get("IMAP_PASSWORD")
    if not all([host, user, password]) or not reference_ids:
        return {}

    found = {}
    ref_pattern = re.compile(r"RESIN8-RFQ-\d{4}")

    with imaplib.IMAP4_SSL(host) as imap:
        imap.login(user, password)
        imap.select("INBOX")
        _, msg_ids = imap.search(None, "UNSEEN")
        for msg_id in msg_ids[0].split():
            _, msg_data = imap.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            subject = msg.get("Subject", "")
            match = ref_pattern.search(subject)
            if not match or match.group(0) not in reference_ids:
                continue

            body_text, attachments = "", []
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition") or "")
                if content_type == "text/plain" and "attachment" not in disposition:
                    body_text += part.get_payload(decode=True).decode(errors="replace")
                elif "attachment" in disposition:
                    filename = part.get_filename()
                    if filename:
                        attachments.append((filename, part.get_payload(decode=True)))

            found[match.group(0)] = {
                "from": msg.get("From", ""),
                "subject": subject,
                "body": body_text,
                "attachments": attachments,
            }

    return found
