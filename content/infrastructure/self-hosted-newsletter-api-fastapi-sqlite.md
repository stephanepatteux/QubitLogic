---
title: "Self-Hosted Newsletter API: FastAPI, SQLite, No Mailchimp"
date: 2026-06-05T12:00:00+01:00
lastmod: 2026-06-06T08:00:00+01:00
draft: false
description: "Build a GDPR-friendly newsletter API with FastAPI, SQLite, double opt-in, and SMTP — on the same VPS as your Hugo blog. No Mailchimp or ConvertKit required."
keywords:
  - "self hosted newsletter api"
  - "fastapi newsletter sqlite"
  - "newsletter without mailchimp"
  - "double opt in gdpr"
  - "hugo newsletter signup"
  - "transactional email smtp"
summary: "Static blog + tiny FastAPI service = full data ownership and ~$6/mo hosting. Double opt-in, token confirm/unsubscribe, Nginx /api routing — the pattern behind QubitLogic's newsletter."
series: ["Phase 1: Infrastructure"]
tags: ["fastapi", "python", "sqlite", "newsletter", "gdpr", "hugo", "nginx", "self-hosted", "infrastructure"]
categories: ["tutorial"]
images: ["/images/og/self-hosted-newsletter-api-fastapi-sqlite.png"]
weight: 5
ShowToc: true
TocOpen: false
faq:
  - q: "Is double opt-in required for a newsletter under GDPR?"
    a: "For UK and EU audiences, double opt-in is the safest consent mechanism: the user submits an email, receives a confirmation link, and only then is marked as subscribed. Single opt-in risks storing emails without provable consent. The ICO direct marketing guidance recommends clear consent records — a confirmed=1 row with timestamp in SQLite is sufficient for a small list."
  - q: "Can SQLite handle a newsletter subscriber list?"
    a: "Easily for lists under 100,000 subscribers. SQLite handles thousands of writes per second on NVMe — far more than a technical blog newsletter needs. If you outgrow it, migrate to PostgreSQL with the same schema; the FastAPI routes stay identical."
  - q: "What DNS records do I need for newsletter emails to arrive?"
    a: "At minimum: SPF (TXT record authorising your SMTP server), DKIM (signing key from Zoho or your mail provider), and DMARC (policy for failed authentication). Without SPF/DKIM, confirmation emails land in spam. Zoho's admin console shows the exact records for your domain."
  - q: "Should I use Listmonk instead of a custom FastAPI newsletter?"
    a: "Listmonk is better for campaigns, analytics, and lists above ~10,000 subscribers — it needs PostgreSQL and Docker. FastAPI + SQLite is better for a technical blog: three routes, double opt-in, zero extra containers, and full control on the same VPS as Hugo. Many developers start with FastAPI and migrate to Listmonk only when they need broadcast campaigns."
  - q: "How do I stop bots spamming my subscribe form?"
    a: "Add an Nginx rate limit on POST /api/newsletter/subscribe (5 requests per minute per IP), a honeypot hidden field bots fill but humans leave empty, and reject disposable email domains in FastAPI. Never expose a public admin endpoint without API key auth."
howto_total_time: "PT2H"
howto_cost: "6"
howto_steps:
  - name: "Understand the architecture"
    text: "Hugo form POSTs to /api/newsletter/subscribe; FastAPI stores pending subscribers in SQLite and sends a confirmation email via SMTP."
  - name: "Implement FastAPI routes"
    text: "Write subscribe, confirm, and unsubscribe endpoints with secrets.token_urlsafe tokens and parameterized SQL."
  - name: "Configure environment and systemd"
    text: "Set SMTP credentials and NEWSLETTER_DB path in .env, load via EnvironmentFile in fastapi.service."
  - name: "Proxy /api/ through Nginx"
    text: "Add a location block proxying /api/ to 127.0.0.1:8000 on your Hugo site server block."
  - name: "Add Hugo subscribe form and verify"
    text: "Wire the form to POST /api/newsletter/subscribe, test double opt-in end-to-end, and check SPF/DKIM if mail goes to spam."
---

## Overview

SaaS newsletter tools charge monthly fees and store your subscriber list on their servers. A **self-hosted newsletter API** on your existing VPS costs almost nothing extra: SQLite for storage, FastAPI for three routes, and SMTP for confirmation emails.

This is the architecture behind [QubitLogic's newsletter](/build-technical-blog-cursor-hugo/) — extracted here as a standalone tutorial you can deploy after [FastAPI on Ubuntu 24.04](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/).

**What you get:**

- `POST /api/newsletter/subscribe` — collect email, send confirm link
- `GET /api/newsletter/confirm?token=…` — double opt-in
- `GET /api/newsletter/unsubscribe?token=…` — one-click removal
- Hugo form posting via `fetch` (no third-party JS widget)

---

## Prerequisites

- [Hardened VPS](/infrastructure/secure-ubuntu-24-04-vps-hardening/) + [FastAPI deploy guide](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) completed
- Domain with HTTPS (e.g. `qubitlogic.dev`)
- SMTP credentials ([Zoho Mail](https://www.zoho.com/mail/) free tier works for low volume)

{{< affiliate_stack >}}

{{< affiliate_box
    name="Zoho Mail"
    url="AFFILIATE_LINK_ZOHO"
    cta="Create free mailbox"
    badge="Transactional SMTP"
    desc="Free tier for a custom-domain mailbox — use SMTP to send confirm/unsubscribe emails from your API."
    offer="Free tier available"
>}}

{{< affiliate_box
    name="Dynadot"
    url="AFFILIATE_LINK_DYNADOT"
    cta="Register your domain"
    badge="Domain registrar"
    desc="Register a .dev or .com domain, then point nameservers to Cloudflare. Ambassador Program — 30% commission on registrations."
    price="From ~$10/yr"
>}}

---

## Step 1 — Architecture

```
Browser → Hugo static page (form)
       → POST /api/newsletter/subscribe
       → FastAPI → SQLite (/var/lib/yoursite/newsletter.db)
       → SMTP → confirmation email with token link
User clicks link → GET /confirm?token=… → confirmed=1
```

UK/EU readers: double opt-in aligns with [ICO direct marketing guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/). Link your [Privacy policy](/privacy/) from every form.

### SaaS vs self-hosted cost

| | Mailchimp (500 contacts) | Self-hosted |
|---|--------------------------|-------------|
| Monthly cost | ~$13+ | $0 (same VPS as blog) |
| Data location | US SaaS servers | Your SQLite file |
| Customisation | Limited | Full FastAPI control |
| GDPR export/erase | Vendor process | `DELETE FROM subscribers` |

For a technical blog with under 5,000 subscribers, self-hosting is cheaper and gives you provable consent records in your own database.

### FastAPI + SQLite vs Listmonk vs Mailchimp

| | Mailchimp | Listmonk (self-hosted) | **FastAPI + SQLite (this guide)** |
|---|-----------|------------------------|-----------------------------------|
| Monthly cost | $13+ at 500 contacts | $0 (+ VPS) | **$0** (same VPS as blog) |
| Setup time | 15 min | 1–2 hrs (Docker + Postgres) | **~1 hr** after FastAPI deploy |
| Double opt-in | Yes | Yes | Yes |
| Broadcast campaigns | Yes | Yes | Build yourself (cron + SMTP) |
| Data ownership | Vendor | Your Postgres | **Your SQLite file** |
| Best for | Non-technical marketers | Newsletter-first sites | **Developer blogs on Hugo** |

Listmonk is excellent when newsletters are the product. For a blog with a signup form in the footer, **50 lines of FastAPI** beats running Postgres and a second Docker stack.

---

## Step 2 — FastAPI application

Install deps in `/opt/api`:

```bash
pip install aiosmtplib python-multipart
```

`newsletter.py` (merge into your app or import):

```python
import os, sqlite3, secrets, smtplib, ssl
from email.message import EmailMessage
from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import HTMLResponse

app = FastAPI()
DB = os.getenv("NEWSLETTER_DB", "/var/lib/qubitlogic/newsletter.db")
SITE = os.getenv("SITE_URL", "https://example.com").rstrip("/")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.zoho.eu")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM = os.getenv("NEWSLETTER_FROM", SMTP_USER)

def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        email TEXT PRIMARY KEY,
        token TEXT UNIQUE NOT NULL,
        confirmed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    return con

def send_mail(to: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

DISPOSABLE = {"mailinator.com", "guerrillamail.com", "tempmail.com"}

@app.post("/api/newsletter/subscribe")
async def subscribe(email: str = Form(...), website: str = Form(default="")):
    # Honeypot — bots fill hidden "website" field; humans leave it empty
    if website:
        return HTMLResponse("<p>Check your email to confirm.</p>")
    email = email.strip().lower()
    if "@" not in email or email.split("@")[-1] in DISPOSABLE:
        raise HTTPException(400, "Invalid email")
    token = secrets.token_urlsafe(32)
    con = db()
    try:
        con.execute("INSERT INTO subscribers (email, token) VALUES (?, ?)", (email, token))
        con.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Already subscribed or pending.")
    link = f"{SITE}/api/newsletter/confirm?token={token}"
    send_mail(email, "Confirm your subscription", f"Click to confirm:\n{link}")
    return HTMLResponse("<p>Check your email to confirm.</p>")

@app.get("/api/newsletter/confirm")
async def confirm(token: str = Query(...)):
    con = db()
    n = con.execute(
        "UPDATE subscribers SET confirmed=1 WHERE token=? AND confirmed=0", (token,)
    ).rowcount
    con.commit()
    if not n:
        raise HTTPException(400, "Invalid or already confirmed.")
    return HTMLResponse("<p>You're subscribed.</p>")

@app.get("/api/newsletter/unsubscribe")
async def unsubscribe(token: str = Query(...)):
    con = db()
    con.execute("DELETE FROM subscribers WHERE token=?", (token,))
    con.commit()
    return HTMLResponse("<p>Unsubscribed.</p>")
```

SQLite docs: [sqlite.org](https://www.sqlite.org/docs.html). FastAPI forms: [fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/request-forms/).

---

## Step 3 — Environment file

```bash
sudo mkdir -p /var/lib/qubitlogic
sudo chown deploy:deploy /var/lib/qubitlogic
nano /opt/api/.env
```

```ini
NEWSLETTER_DB=/var/lib/qubitlogic/newsletter.db
SITE_URL=https://yourdomain.dev
SMTP_HOST=smtp.zoho.eu
SMTP_PORT=587
SMTP_USER=news@yourdomain.dev
SMTP_PASS=your-app-password
NEWSLETTER_FROM=news@yourdomain.dev
```

Load in systemd: add `EnvironmentFile=/opt/api/.env` under `[Service]` in `fastapi.service`, then `sudo systemctl restart fastapi`.

Zoho SMTP setup: [zoho.com/mail/help/zoho-smtp](https://www.zoho.com/mail/help/zoho-smtp.html).

### SPF, DKIM, and DMARC (deliverability)

Confirmation emails that land in spam usually mean missing DNS authentication. After connecting Zoho (or any SMTP provider), add these records at your DNS host (Cloudflare → DNS):

| Record | Purpose | Example |
|--------|---------|---------|
| SPF (TXT) | Authorises Zoho to send for your domain | `v=spf1 include:zoho.eu ~all` |
| DKIM (TXT/CNAME) | Cryptographic signature on outbound mail | Copy from Zoho admin → Email Authentication |
| DMARC (TXT) | Policy when SPF/DKIM fail | `v=DMARC1; p=none; rua=mailto:you@domain` |

Verify with [mail-tester.com](https://www.mail-tester.com/) after sending a test confirmation. Score 8+/10 before promoting the signup form publicly.

---

## Step 4 — Nginx route `/api/` + rate limit

Add to `/etc/nginx/nginx.conf` (http block) once:

```nginx
limit_req_zone $binary_remote_addr zone=newsletter:10m rate=5r/m;
```

If Hugo serves the root site, proxy only API paths:

```nginx
location /api/newsletter/subscribe {
    limit_req zone=newsletter burst=2 nodelay;
    limit_req_status 429;
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

`5r/m` = five subscribe attempts per IP per minute — enough for humans, blocks list-bombing bots. Reload: `sudo nginx -t && sudo systemctl reload nginx`.

Full rate-limit patterns: [Nginx reverse proxy hardening](/infrastructure/nginx-reverse-proxy-python-ai-api/).

---

## Step 5 — Hugo subscribe form

In a partial or page:

```html
<form class="ql-subscribe-form" action="/api/newsletter/subscribe" method="POST">
  <label for="email">Email</label>
  <input type="email" name="email" id="email" required autocomplete="email">
  <!-- Honeypot: hide with CSS, leave empty -->
  <input type="text" name="website" tabindex="-1" autocomplete="off" hidden aria-hidden="true">
  <button type="submit" class="ql-subscribe-btn">Subscribe</button>
  <p class="ql-subscribe-msg" hidden></p>
</form>
<p><small>Double opt-in. <a href="/privacy/">Privacy policy</a>.</small></p>
```

QubitLogic already wires `.ql-subscribe-form` in `extend_footer.html` for AJAX submit — copy that pattern from [the full build guide](/build-technical-blog-cursor-hugo/).

---

## Verification

1. `curl -X POST -F email=test@example.com https://yourdomain.dev/api/newsletter/subscribe`
2. Check inbox for confirm link (also check spam)
3. Click confirm → DB row `confirmed=1`
4. Unsubscribe link removes row

```bash
sqlite3 /var/lib/qubitlogic/newsletter.db "SELECT email, confirmed FROM subscribers;"
```

---

## Troubleshooting

**Emails not arriving** — Verify SPF/DKIM on your domain DNS; Zoho admin console shows required records.

**403 from Nginx** — `client_max_body_size` too small (unlikely for email); check SELinux/AppArmor only if enabled.

**CORS errors** — Same-origin form POST avoids CORS; for SPA use explicit `CORSMiddleware` in FastAPI.

**429 Too Many Requests** — Nginx rate limit triggered. Normal if you tested repeatedly; wait 60s or tune `rate=5r/m`.

### GDPR data export and erasure

UK/EU users can request their data. One-liner export:

```bash
sqlite3 /var/lib/qubitlogic/newsletter.db ".mode csv" "SELECT * FROM subscribers WHERE email='user@example.com';"
```

Erasure (right to be forgotten):

```bash
sqlite3 /var/lib/qubitlogic/newsletter.db "DELETE FROM subscribers WHERE email='user@example.com';"
```

Document this process in your [Privacy policy](/privacy/).

---

## Frequently Asked Questions

### Is double opt-in required for a newsletter under GDPR?

For UK and EU audiences, double opt-in is the safest consent mechanism. Single opt-in risks storing emails without provable consent. A `confirmed=1` row with timestamp in SQLite is sufficient for a small list.

### Can SQLite handle a newsletter subscriber list?

Easily for lists under 100,000 subscribers. If you outgrow it, migrate to PostgreSQL with the same schema.

### What DNS records do I need for newsletter emails to arrive?

SPF, DKIM, and DMARC at your DNS host. Verify with [mail-tester.com](https://www.mail-tester.com/) before promoting the form.

### Should I use Listmonk instead of a custom FastAPI newsletter?

Listmonk for campaigns and large lists; FastAPI + SQLite for developer blogs with a footer signup form.

### How do I stop bots spamming my subscribe form?

Nginx rate limit (5/min per IP), honeypot field, and reject disposable domains — all included in this guide.

---

## Next steps

1. [Newsletter broadcasts: Cron, RSS & SMTP](/infrastructure/self-hosted-newsletter-broadcast-cron-rss/) — weekly sends from `index.xml`
2. [Cloudflare in front of static + API](/infrastructure/cloudflare-nginx-vps-static-site-api/)
3. [Deploy Hugo via GitHub Actions](/infrastructure/deploy-hugo-github-actions-vps/)
4. [CI/CD for the API repo](/infrastructure/cicd-pipeline-ai-python-scripts/)

---

*Affiliate links may appear in partner boxes. [Affiliate Disclosure](/affiliate-disclosure/).*
