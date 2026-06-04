#!/usr/bin/env python3
"""
One-off test: fetch latest RSS post and email it to a single address.
Does NOT use the subscriber DB — for manual testing only.

Usage (PowerShell):
  $env:SMTP_PASSWORD="your-zoho-app-password"
  python newsletter\test_send.py stephanepatteux@gmail.com
"""
import os, sys, smtplib, ssl
import xml.etree.ElementTree as ET
from email.message import EmailMessage
from urllib.request import urlopen

RSS_URL   = "https://qubitlogic.dev/index.xml"
SITE_URL  = "https://qubitlogic.dev"
FROM_ADDR = os.getenv("EMAIL_FROM",    "QubitLogic <hello@qubitlogic.dev>")
SMTP_HOST = os.getenv("SMTP_HOST",     "smtppro.zoho.eu")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER",     "hello@qubitlogic.dev")
SMTP_PASS = os.getenv("SMTP_PASSWORD", "")

TO = sys.argv[1] if len(sys.argv) > 1 else "stephanepatteux@gmail.com"

if not SMTP_PASS:
    print("ERROR: set SMTP_PASSWORD environment variable first")
    print("  PowerShell:  $env:SMTP_PASSWORD='your-app-password'")
    sys.exit(1)

# ── Fetch latest post ─────────────────────────────────────────────────────────
print(f"Fetching RSS from {RSS_URL} …")
with urlopen(RSS_URL, timeout=15) as r:
    root = ET.fromstring(r.read())

item = root.find("channel/item")
if item is None:
    print("No items in RSS feed"); sys.exit(1)

def txt(tag):
    el = item.find(tag)
    return el.text.strip() if el is not None and el.text else ""

post = {
    "title":       txt("title"),
    "link":        txt("link"),
    "description": txt("description") or "A new tutorial is live on QubitLogic.",
}
print(f"Latest post: {post['title']}")
print(f"Link:        {post['link']}")

# ── Build email ───────────────────────────────────────────────────────────────
subject = f"[TEST] New on QubitLogic: {post['title']}"

text = (
    f"[TEST EMAIL — not sent to real subscribers]\n\n"
    f"New on QubitLogic: {post['title']}\n\n"
    f"{post['description']}\n\n"
    f"Read the article: {post['link']}\n\n"
    "---\nThis was a test send from newsletter/test_send.py"
)

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:32px 16px;background:#0a0a0a;font-family:system-ui,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <table cellpadding="0" cellspacing="0"
             style="max-width:560px;width:100%;background:#161616;border:1px solid #2a2a2a;border-radius:12px;overflow:hidden;">
        <tr><td style="background:#111;padding:18px 32px;border-bottom:1px solid #2a2a2a;">
          <p style="margin:0;font-size:1rem;font-weight:700;color:#00e87a;">QubitLogic</p>
          <p style="margin:4px 0 0;font-size:0.75rem;color:#475569;">Weekly quantum &amp; AI developer digest</p>
        </td></tr>
        <tr><td style="padding:32px;">
          <p style="margin:0 0 6px;font-size:0.75rem;font-weight:600;color:#f59e0b;text-transform:uppercase;letter-spacing:.06em;">
            ⚠ Test email — not sent to subscribers
          </p>
          <p style="margin:0 0 6px;font-size:0.75rem;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:.06em;">New tutorial</p>
          <h1 style="margin:0 0 16px;font-size:1.2rem;line-height:1.35;color:#e2e8f0;font-weight:700;">
            {post['title']}
          </h1>
          <p style="margin:0 0 28px;color:#94a3b8;line-height:1.65;font-size:0.9rem;">
            {post['description']}
          </p>
          <a href="{post['link']}"
             style="display:inline-block;background:#00e87a;color:#000;font-weight:700;
                    text-decoration:none;padding:13px 28px;border-radius:8px;font-size:0.95rem;">
            Read article →
          </a>
        </td></tr>
        <tr><td style="background:#111;padding:16px 32px;border-top:1px solid #2a2a2a;">
          <p style="margin:0;font-size:0.75rem;color:#475569;">
            Test send via newsletter/test_send.py — not sent to real subscribers.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

# ── Send ─────────────────────────────────────────────────────────────────────
msg = EmailMessage()
msg["Subject"] = subject
msg["From"]    = FROM_ADDR
msg["To"]      = TO
msg.set_content(text)
msg.add_alternative(html, subtype="html")

ctx = ssl.create_default_context()

# Try port 465 (SSL) first, fall back to 587 (STARTTLS)
sent = False
for port, use_ssl in [(465, True), (587, False)]:
    try:
        print(f"\nTrying {SMTP_HOST}:{port} ({'SSL' if use_ssl else 'STARTTLS'}) …")
        if use_ssl:
            with smtplib.SMTP_SSL(SMTP_HOST, port, context=ctx) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, port) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        sent = True
        break
    except Exception as e:
        print(f"  ✗ Failed on port {port}: {e}")

if not sent:
    print("\nERROR: Both ports failed — your network may block outbound SMTP.")
    print("The VPS won't have this issue. Test will work once install.sh is run.")
    sys.exit(1)

print(f"✓ Sent to {TO}")
print("Check your inbox (and spam folder if not there).")
