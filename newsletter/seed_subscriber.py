#!/usr/bin/env python3
"""Insert or confirm a newsletter subscriber (run on VPS after setup-api)."""
import os, secrets, sqlite3, sys
from pathlib import Path

for ep in (Path(__file__).parent / ".env", Path("/etc/qubitlogic/newsletter.env")):
    if ep.exists():
        for line in ep.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
        break

DB = os.getenv("NEWSLETTER_DB", "/var/lib/qubitlogic/newsletter.db")
email = (sys.argv[1] if len(sys.argv) > 1 else "stephanepatteux@gmail.com").strip().lower()

os.makedirs(os.path.dirname(DB), exist_ok=True)
con = sqlite3.connect(DB)
con.execute("""
    CREATE TABLE IF NOT EXISTS subscribers (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        confirm_token TEXT UNIQUE NOT NULL,
        unsub_token TEXT UNIQUE NOT NULL,
        confirmed INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
""")
row = con.execute("SELECT confirmed FROM subscribers WHERE email=?", (email,)).fetchone()
if row:
    if not row[0]:
        con.execute("UPDATE subscribers SET confirmed=1 WHERE email=?", (email,))
        print(f"Confirmed existing subscriber: {email}")
    else:
        print(f"Already confirmed: {email}")
else:
    con.execute(
        "INSERT INTO subscribers (email, confirm_token, unsub_token, confirmed) VALUES (?,?,?,1)",
        (email, secrets.token_urlsafe(32), secrets.token_urlsafe(32)),
    )
    print(f"Added confirmed subscriber: {email}")
con.commit()
