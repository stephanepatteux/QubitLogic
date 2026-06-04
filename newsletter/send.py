#!/usr/bin/env python3
"""
QubitLogic weekly newsletter sender
------------------------------------
Reads the RSS feed, emails confirmed subscribers with the latest post.
Skips silently if:
  - No confirmed subscribers
  - Latest post GUID matches last-sent record (nothing new)
  - Latest post is older than MAX_POST_AGE_DAYS (stale)
  - RSS feed is unreachable or malformed

Run manually:
  python3 send.py                 # normal send
  python3 send.py --dry-run       # parse + log, no emails sent
  python3 send.py --force         # ignore last-sent check, re-send latest

Environment (loaded from /etc/qubitlogic/newsletter.env if it exists):
  NEWSLETTER_DB   SQLite path  (default: /var/lib/qubitlogic/newsletter.db)
  NEWSLETTER_STATE  last-sent file (default: /var/lib/qubitlogic/last_sent_guid.txt)
  SITE_URL        https://qubitlogic.dev
  EMAIL_FROM      QubitLogic <hello@qubitlogic.dev>
  SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD
"""

import os, sys, sqlite3, smtplib, ssl, time, logging
import xml.etree.ElementTree as ET
from email.message import EmailMessage
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

# ── Env ───────────────────────────────────────────────────────────────────────

def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# Check sibling .env first, then system-wide path
_load_env_file(Path(__file__).parent / ".env")
_load_env_file(Path("/etc/qubitlogic/newsletter.env"))

DB_PATH      = os.getenv("NEWSLETTER_DB",    "/var/lib/qubitlogic/newsletter.db")
STATE_PATH   = os.getenv("NEWSLETTER_STATE", "/var/lib/qubitlogic/last_sent_guid.txt")
RSS_URL      = os.getenv("RSS_URL",          "https://qubitlogic.dev/index.xml")
SITE_URL     = os.getenv("SITE_URL",         "https://qubitlogic.dev")
FROM_ADDR    = os.getenv("EMAIL_FROM",       "QubitLogic <hello@qubitlogic.dev>")
SMTP_HOST    = os.getenv("SMTP_HOST",        "smtppro.zoho.eu")
SMTP_PORT    = int(os.getenv("SMTP_PORT",    "587"))
SMTP_USER    = os.getenv("SMTP_USER",        "hello@qubitlogic.dev")
SMTP_PASS    = os.getenv("SMTP_PASSWORD",    "")
MAX_AGE_DAYS = int(os.getenv("MAX_POST_AGE_DAYS", "14"))
SEND_DELAY   = float(os.getenv("SEND_DELAY_MS", "200")) / 1000   # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("newsletter.send")

# ── RSS ───────────────────────────────────────────────────────────────────────

def fetch_latest_post() -> dict | None:
    """Return the most recent RSS item as a dict, or None on failure."""
    try:
        with urlopen(RSS_URL, timeout=15) as r:
            raw = r.read()
    except URLError as e:
        log.error("Could not fetch RSS: %s", e)
        return None

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        log.error("Could not parse RSS: %s", e)
        return None

    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    channel = root.find("channel")
    if channel is None:
        log.error("No <channel> in RSS")
        return None

    item = channel.find("item")
    if item is None:
        log.info("RSS has no items — nothing to send")
        return None

    def txt(tag: str) -> str:
        el = item.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    post = {
        "title":       txt("title"),
        "link":        txt("link"),
        "guid":        txt("guid") or txt("link"),
        "description": txt("description"),
        "pubDate":     txt("pubDate"),
    }
    if not post["title"] or not post["link"]:
        log.error("Latest RSS item missing title or link")
        return None

    return post

# ── State ─────────────────────────────────────────────────────────────────────

def last_sent_guid() -> str:
    p = Path(STATE_PATH)
    return p.read_text().strip() if p.exists() else ""

def save_sent_guid(guid: str) -> None:
    Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(STATE_PATH).write_text(guid)

def post_is_stale(pub_date_str: str) -> bool:
    """Return True if the post is older than MAX_AGE_DAYS."""
    if not pub_date_str:
        return False   # no date → don't block
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(pub_date_str)
        age = (datetime.now(timezone.utc) - dt).days
        return age > MAX_AGE_DAYS
    except Exception:
        return False

# ── Database ──────────────────────────────────────────────────────────────────

def get_confirmed_subscribers() -> list[dict]:
    if not Path(DB_PATH).exists():
        return []
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT email, unsub_token FROM subscribers WHERE confirmed=1"
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]

# ── Email template ────────────────────────────────────────────────────────────

def build_email(post: dict, unsub_url: str) -> tuple[str, str]:
    title       = post["title"]
    link        = post["link"]
    description = post["description"] or "A new tutorial is live on QubitLogic — open the link below to read it."

    text = (
        f"New on QubitLogic: {title}\n\n"
        f"{description}\n\n"
        f"Read the article: {link}\n\n"
        "---\n"
        f"You're receiving this because you subscribed at {SITE_URL}.\n"
        f"Unsubscribe: {unsub_url}"
    )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:32px 16px;background:#0a0a0a;font-family:system-ui,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <table cellpadding="0" cellspacing="0"
             style="max-width:560px;width:100%;background:#161616;border:1px solid #2a2a2a;border-radius:12px;overflow:hidden;">
        <tr><td style="background:#111;padding:18px 32px;border-bottom:1px solid #2a2a2a;">
          <p style="margin:0;font-size:1rem;font-weight:700;color:#00e87a;letter-spacing:-.01em;">QubitLogic</p>
          <p style="margin:4px 0 0;font-size:0.75rem;color:#475569;">Weekly quantum &amp; AI developer digest</p>
        </td></tr>
        <tr><td style="padding:32px;">
          <p style="margin:0 0 6px;font-size:0.75rem;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:.06em;">New tutorial</p>
          <h1 style="margin:0 0 16px;font-size:1.2rem;line-height:1.35;color:#e2e8f0;font-weight:700;">{title}</h1>
          <p style="margin:0 0 28px;color:#94a3b8;line-height:1.65;font-size:0.9rem;">{description}</p>
          <a href="{link}"
             style="display:inline-block;background:#00e87a;color:#000;font-weight:700;text-decoration:none;padding:13px 28px;border-radius:8px;font-size:0.95rem;">
            Read article →
          </a>
        </td></tr>
        <tr><td style="background:#111;padding:16px 32px;border-top:1px solid #2a2a2a;">
          <p style="margin:0;font-size:0.75rem;color:#475569;line-height:1.5;">
            You're receiving this because you subscribed at
            <a href="{SITE_URL}" style="color:#475569;">{SITE_URL.replace("https://","")}</a>.<br>
            <a href="{unsub_url}" style="color:#475569;">Unsubscribe</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

    return text, html

# ── Send ──────────────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, text: str, html: str) -> bool:
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"]    = FROM_ADDR
        msg["To"]      = to
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        log.error("SMTP error sending to %s: %s", to, e)
        return False

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    dry_run = "--dry-run" in sys.argv
    force   = "--force"   in sys.argv

    if dry_run:
        log.info("DRY RUN — no emails will be sent")

    # 1. Fetch RSS
    post = fetch_latest_post()
    if not post:
        log.info("No post found — skipping")
        sys.exit(0)

    log.info("Latest post: %s (%s)", post["title"], post["guid"])

    # 2. Already sent?
    if not force and post["guid"] == last_sent_guid():
        log.info("Already sent this post (guid matches) — skipping")
        sys.exit(0)

    # 3. Too old?
    if post_is_stale(post["pubDate"]):
        log.info("Post is older than %d days — skipping", MAX_AGE_DAYS)
        sys.exit(0)

    # 4. Any subscribers?
    subs = get_confirmed_subscribers()
    if not subs:
        log.info("No confirmed subscribers yet — skipping")
        sys.exit(0)

    log.info("Sending to %d subscriber(s)%s", len(subs), " (dry run)" if dry_run else "")

    # 5. Send
    subject  = f"New on QubitLogic: {post['title']}"
    ok_count = 0
    fail_count = 0

    for sub in subs:
        unsub_url = f"{SITE_URL}/api/newsletter/unsubscribe?token={sub['unsub_token']}"
        text, html = build_email(post, unsub_url)

        if dry_run:
            log.info("  [DRY RUN] Would send to: %s", sub["email"])
            ok_count += 1
            continue

        ok = send_email(sub["email"], subject, text, html)
        if ok:
            log.info("  Sent → %s", sub["email"])
            ok_count += 1
        else:
            fail_count += 1
        time.sleep(SEND_DELAY)

    log.info("Done — %d sent, %d failed", ok_count, fail_count)

    # 6. Record guid only if all succeeded
    if not dry_run and fail_count == 0 and ok_count > 0:
        save_sent_guid(post["guid"])
        log.info("Saved last-sent guid: %s", post["guid"])
    elif fail_count > 0:
        log.warning("Partial failures — guid NOT saved; will retry next run")

if __name__ == "__main__":
    main()
