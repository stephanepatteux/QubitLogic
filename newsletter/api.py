"""
QubitLogic Newsletter API  (runs on VPS via systemd)
----------------------------------------------------
POST /api/newsletter/subscribe    — add pending subscriber, send confirm email
GET  /api/newsletter/confirm      — ?token=...  activate subscriber
GET  /api/newsletter/unsubscribe  — ?token=...  remove subscriber

Environment (loaded from /etc/qubitlogic/newsletter.env):
  NEWSLETTER_DB   path to SQLite file  (default: /var/lib/qubitlogic/newsletter.db)
  SITE_URL        public site URL      (default: https://qubitlogic.dev)
  EMAIL_FROM      MIME From header     (default: QubitLogic <hello@qubitlogic.dev>)
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
"""

import os, sqlite3, secrets, smtplib, ssl, logging, time
from contextlib import asynccontextmanager
from email.message import EmailMessage
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("newsletter.api")

# Load env file — sibling .env first, then system-wide path
from pathlib import Path as _Path
for _ep in (_Path(__file__).parent / ".env", _Path("/etc/qubitlogic/newsletter.env")):
    if _ep.exists():
        for _ln in _ep.read_text().splitlines():
            _ln = _ln.strip()
            if _ln and not _ln.startswith("#") and "=" in _ln:
                _k, _, _v = _ln.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())
        break

DB_PATH   = os.getenv("NEWSLETTER_DB",   "/var/lib/qubitlogic/newsletter.db")
SITE_URL  = os.getenv("SITE_URL",        "https://qubitlogic.dev")
FROM_ADDR = os.getenv("EMAIL_FROM",      "QubitLogic <hello@qubitlogic.dev>")
SMTP_HOST = os.getenv("SMTP_HOST",       "smtppro.zoho.eu")
SMTP_PORT = int(os.getenv("SMTP_PORT",   "587"))
SMTP_USER = os.getenv("SMTP_USER",       "hello@qubitlogic.dev")
SMTP_PASS = os.getenv("SMTP_PASSWORD",   "")

# ── Database ─────────────────────────────────────────────────────────────────

def _db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def _init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id            INTEGER PRIMARY KEY,
                email         TEXT    UNIQUE NOT NULL,
                confirm_token TEXT    UNIQUE NOT NULL,
                unsub_token   TEXT    UNIQUE NOT NULL,
                confirmed     INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_db()
    yield

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[SITE_URL],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# ── Email ─────────────────────────────────────────────────────────────────────

def _send(to: str, subject: str, text: str, html: str) -> None:
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
    log.info("Sent confirm email to %s", to)

def _confirm_email(confirm_url: str) -> tuple[str, str]:
    text = (
        "Thanks for signing up to QubitLogic.\n\n"
        "Click the link below to confirm your subscription:\n\n"
        f"{confirm_url}\n\n"
        "If you didn't sign up, ignore this email.\n\n— QubitLogic"
    )
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:32px 16px;background:#0a0a0a;font-family:system-ui,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <table cellpadding="0" cellspacing="0"
             style="max-width:520px;width:100%;background:#161616;border:1px solid #2a2a2a;border-radius:12px;overflow:hidden;">
        <tr><td style="background:#111;padding:20px 32px;border-bottom:1px solid #2a2a2a;">
          <p style="margin:0;font-size:1rem;font-weight:700;color:#00e87a;">QubitLogic</p>
        </td></tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;font-size:1.15rem;color:#e2e8f0;">
            Confirm your subscription
          </h2>
          <p style="margin:0 0 24px;color:#94a3b8;line-height:1.6;font-size:0.9rem;">
            One tutorial per week — quantum algorithms, AI infrastructure, Python you can run.
            Click below to activate.
          </p>
          <a href="{confirm_url}"
             style="display:inline-block;background:#00e87a;color:#000;font-weight:700;
                    text-decoration:none;padding:12px 24px;border-radius:8px;font-size:0.95rem;">
            Confirm subscription →
          </a>
          <p style="margin:24px 0 0;font-size:0.75rem;color:#475569;">
            If you didn't sign up, ignore this email. No action needed.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""
    return text, html

# ── Helpers ───────────────────────────────────────────────────────────────────

def _page(heading: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{heading} — QubitLogic</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:32px 16px;background:#0a0a0a;color:#e2e8f0;
     font-family:system-ui,sans-serif;display:flex;align-items:center;
     justify-content:center;min-height:100vh}}
.card{{max-width:440px;width:100%;background:#161616;border:1px solid #2a2a2a;
       border-radius:12px;padding:2rem;text-align:center}}
h1{{margin:0 0 .75rem;font-size:1.3rem;color:#00e87a}}
p{{margin:0 0 1rem;color:#94a3b8;line-height:1.6;font-size:.9rem}}
a{{color:#00e87a;font-weight:600;text-decoration:none}}
</style></head>
<body><div class="card">
<h1>{heading}</h1>{body}
</div></body></html>"""

# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/newsletter/subscribe", response_class=HTMLResponse)
async def subscribe(
    request: Request,
    email: Annotated[str, Form()],
    website: Annotated[str, Form()] = "",   # honeypot — bots fill this
):
    # Honeypot check
    if website.strip():
        return HTMLResponse(_page("Thanks", "<p>Thanks for signing up.</p>"))

    email = email.strip().lower()
    if not email or "@" not in email or len(email) > 254 or "." not in email.split("@")[-1]:
        return HTMLResponse(_page("Invalid email",
            "<p>That doesn't look like a valid email address.</p>"
            f"<p><a href='{SITE_URL}/newsletter/'>Try again</a></p>"))

    confirm_tok = secrets.token_urlsafe(32)
    unsub_tok   = secrets.token_urlsafe(32)

    try:
        with _db() as con:
            row = con.execute(
                "SELECT confirmed FROM subscribers WHERE email=?", (email,)
            ).fetchone()
            if row:
                if row["confirmed"]:
                    return HTMLResponse(_page(
                        "Already subscribed",
                        "<p>That email is already confirmed.</p>"
                        f"<p><a href='{SITE_URL}'>← Back to QubitLogic</a></p>",
                    ))
                # Resend confirm with fresh token
                con.execute(
                    "UPDATE subscribers SET confirm_token=? WHERE email=?",
                    (confirm_tok, email),
                )
            else:
                con.execute(
                    "INSERT INTO subscribers (email, confirm_token, unsub_token) VALUES (?,?,?)",
                    (email, confirm_tok, unsub_tok),
                )
    except Exception:
        log.exception("DB error during subscribe")
        raise HTTPException(500, "Server error")

    confirm_url = f"{SITE_URL}/api/newsletter/confirm?token={confirm_tok}"
    try:
        text, html = _confirm_email(confirm_url)
        _send(email, "Confirm your QubitLogic subscription", text, html)
    except Exception:
        log.exception("SMTP error during subscribe")
        raise HTTPException(500, "Could not send confirmation email — please try again shortly")

    return HTMLResponse(_page(
        "Check your email",
        f"<p>We sent a confirmation link to <strong>{email}</strong>.</p>"
        "<p>Click it to activate your subscription.</p>"
        f"<p><a href='{SITE_URL}'>← Back to QubitLogic</a></p>",
    ))


@app.get("/api/newsletter/confirm", response_class=HTMLResponse)
async def confirm(token: str = Query(...)):
    try:
        with _db() as con:
            row = con.execute(
                "SELECT email FROM subscribers WHERE confirm_token=? AND confirmed=0",
                (token,),
            ).fetchone()
            if not row:
                return HTMLResponse(_page(
                    "Link expired",
                    "<p>This confirmation link has already been used or has expired.</p>"
                    f"<p><a href='{SITE_URL}/newsletter/'>Sign up again</a></p>",
                ))
            con.execute(
                "UPDATE subscribers SET confirmed=1, confirm_token='' WHERE confirm_token=?",
                (token,),
            )
    except Exception:
        log.exception("DB error during confirm")
        raise HTTPException(500, "Server error")

    return HTMLResponse(_page(
        "You're subscribed!",
        "<p>Welcome to the QubitLogic weekly digest.</p>"
        "<p>You'll receive the next tutorial on Tuesday morning.</p>"
        f"<p><a href='{SITE_URL}'>← Back to QubitLogic</a></p>",
    ))


@app.get("/api/newsletter/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(token: str = Query(...)):
    try:
        with _db() as con:
            row = con.execute(
                "SELECT email FROM subscribers WHERE unsub_token=?", (token,)
            ).fetchone()
            if not row:
                return HTMLResponse(_page(
                    "Not found",
                    "<p>This unsubscribe link is invalid or has already been used.</p>"
                    f"<p><a href='{SITE_URL}'>← Back to QubitLogic</a></p>",
                ))
            con.execute("DELETE FROM subscribers WHERE unsub_token=?", (token,))
    except Exception:
        log.exception("DB error during unsubscribe")
        raise HTTPException(500, "Server error")

    return HTMLResponse(_page(
        "Unsubscribed",
        "<p>You've been removed from the QubitLogic mailing list.</p>"
        "<p>No further emails will be sent to you.</p>"
        f"<p><a href='{SITE_URL}'>← Back to QubitLogic</a></p>",
    ))


@app.get("/api/newsletter/health")
async def health():
    return {"ok": True}
