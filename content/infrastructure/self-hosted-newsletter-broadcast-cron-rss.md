---
title: "Self-Hosted Newsletter Broadcasts: Cron, RSS & SMTP"
date: 2026-06-30T08:00:00+01:00
lastmod: 2026-06-30T08:00:00+01:00
draft: false
description: "Turn a self-hosted Hugo newsletter into a weekly broadcast system with RSS, SMTP, and GitHub Actions cron — using QubitLogic's actual `newsletter/send.py` and `newsletter.yml` patterns."
keywords:
  - "self hosted newsletter broadcast"
  - "rss email newsletter cron"
  - "github actions cron newsletter"
  - "smtp newsletter python"
  - "hugo rss newsletter"
  - "newsletter send py sqlite"
summary: "QubitLogic sends one weekly article from `index.xml` to confirmed subscribers only: `newsletter/send.py` reads RSS, skips duplicates, and GitHub Actions runs it every Tuesday at 09:00 UTC."
series: ["Phase 1: Infrastructure"]
tags: ["newsletter", "python", "smtp", "rss", "github-actions", "sqlite", "fastapi", "hugo", "infrastructure"]
categories: ["tutorial"]
images: ["/images/og/self-hosted-newsletter-broadcast-cron-rss.png"]
weight: 17
ShowToc: true
TocOpen: false
faq:
  - q: "Why does QubitLogic send the newsletter on Tuesday rather than immediately after publishing?"
    a: "Because the editorial cadence is Monday publish, Tuesday send. Publishing on Monday gives the article time to deploy, enter RSS, and settle in Search Console and social previews; Tuesday 09:00 UTC then sends a clean weekly digest. That is simpler than sending instantly on every post and avoids bombarding subscribers during editing or same-day updates."
  - q: "Does `newsletter/send.py` email only confirmed subscribers?"
    a: "Yes. The script queries `SELECT email, unsub_token FROM subscribers WHERE confirmed=1`, so pending sign-ups are ignored until the user clicks the confirmation link. That preserves the double opt-in flow from the API tutorial."
  - q: "How do I test the broadcast flow safely?"
    a: "Subscribe with a real address, click the confirmation email, confirm the SQLite row shows `confirmed=1`, then run `python3 newsletter/send.py --dry-run` or use the GitHub Actions `test-send` mode. Dry run proves RSS parsing and subscriber selection without emailing the full list."
  - q: "What stops the same article being emailed twice?"
    a: "QubitLogic stores the latest sent GUID in `NEWSLETTER_STATE` and compares it with the newest RSS item. A normal run skips if the GUID matches; `--force` overrides that check when you intentionally want to resend."
  - q: "Should I use Mailchimp, Beehiiv, or Listmonk instead?"
    a: "If your newsletter is the product, Beehiiv or Listmonk may be worth it. If your site is primarily a technical blog and you want one weekly broadcast from your own RSS feed, `send.py` plus SQLite is far cheaper, easier to audit, and keeps subscriber data on your own VPS."
howto_total_time: "PT50M"
howto_cost: "0"
howto_steps:
  - name: "Start from the newsletter API"
    text: "Use the existing FastAPI + SQLite double opt-in stack so subscribers land in the same database and only confirmed rows are eligible for broadcasts."
  - name: "Review `newsletter/send.py`"
    text: "The sender loads `.env`, reads `index.xml`, skips stale or already-sent posts, and emails confirmed subscribers only via SMTP."
  - name: "Schedule weekly sends with GitHub Actions"
    text: "Use `newsletter.yml` with cron `0 9 * * 2` for Tuesday 09:00 UTC, plus manual `dry-run`, `test-send`, `send`, and `force-send` modes."
  - name: "Adopt Monday publish / Tuesday send"
    text: "Publish articles on Monday so RSS, deploys, and metadata are ready before the Tuesday morning send window."
  - name: "Subscribe, confirm, and test end-to-end"
    text: "Add a real address, click the confirmation email, verify `confirmed=1` in SQLite, then run dry-run or test-send before the first live broadcast."
---

## Overview

This article is the **broadcast layer** that follows [Self-Hosted Newsletter API: FastAPI, SQLite, No Mailchimp](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/).

The API tutorial gets you:

- `POST /api/newsletter/subscribe`
- `GET /api/newsletter/confirm`
- `GET /api/newsletter/unsubscribe`
- SQLite subscriber storage
- SMTP confirmation emails

This guide adds the next piece: **send one published article per week to confirmed subscribers only**, using the site's RSS feed and a scheduled GitHub Actions workflow.

QubitLogic's actual pattern is deliberately small:

- `newsletter/send.py` fetches `https://qubitlogic.dev/index.xml`
- it reads only the latest RSS item
- it skips sends when the post is stale or already sent
- it selects only `confirmed=1` subscribers
- `.github/workflows/newsletter.yml` runs it every **Tuesday 09:00 UTC**

That is enough for a weekly engineering newsletter without handing your list to a SaaS platform.

### At a glance

| Item | Value |
|------|-------|
| Time | ~50 minutes |
| Cost | $0 extra on the existing VPS |
| Trigger | GitHub Actions cron (`0 9 * * 2`) |
| Source | `index.xml` RSS feed |
| Audience | Confirmed subscribers only |

### Broadcast options compared

| | Mailchimp / Beehiiv | Listmonk | QubitLogic pattern |
|---|--------------------|----------|--------------------|
| Data ownership | Vendor | Yours | **Yours** |
| Source of truth | Vendor editor | Internal DB + campaign UI | **RSS + SQLite** |
| Weekly blog digest | Yes | Yes | **Yes** |
| Setup overhead | Low | Medium | **Low** |
| Cost at small scale | Monthly SaaS fee | VPS + Postgres | **Existing VPS only** |
| Best for | Marketing-led newsletters | Newsletter-heavy products | **Technical blogs** |

### Scheduler options compared

| Scheduler | Good at | Trade-off |
|-----------|---------|-----------|
| GitHub Actions cron | Tied to the repo, visible logs, manual dispatch modes | Slight schedule jitter is normal |
| System `cron` on the VPS | No GitHub dependency | Harder to review and test from the repo |
| SaaS automation | Turnkey | Less control, more cost |

For QubitLogic, GitHub Actions wins because the site and newsletter code already live in Git, so the schedule, modes, and secrets stay in the same place as the content.

---

## Prerequisites

- The API setup from [Self-Hosted Newsletter API: FastAPI, SQLite, No Mailchimp](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/)
- A working SMTP account and `.env` file on the VPS
- Hugo generating `index.xml` at your site root
- GitHub Actions enabled for the repository

{{< affiliate_stack >}}

{{< callout type="warning" title="Do not skip confirmation testing" >}}
The broadcast script deliberately ignores unconfirmed rows. Before you debug cron, make sure you have subscribed with a real address and clicked the confirmation link so your row shows `confirmed=1`.

On QubitLogic, `deploy.yml` and `setup-api` also run `newsletter/seed_subscriber.py` to add `stephanepatteux@gmail.com` as **confirmed** for weekly send testing — no manual SQL required after deploy.
{{< /callout >}}

---

## Step 1 — Understand what `newsletter/send.py` actually does

The QubitLogic sender is small because it relies on existing site outputs instead of a campaign editor.

At startup it loads environment from a sibling `.env` file or `/etc/qubitlogic/newsletter.env`, then sets sensible defaults:

```python
DB_PATH      = os.getenv("NEWSLETTER_DB",    "/var/lib/qubitlogic/newsletter.db")
STATE_PATH   = os.getenv("NEWSLETTER_STATE", "/var/lib/qubitlogic/last_sent_guid.txt")
RSS_URL      = os.getenv("RSS_URL",          "https://qubitlogic.dev/index.xml")
SITE_URL     = os.getenv("SITE_URL",         "https://qubitlogic.dev")
FROM_ADDR    = os.getenv("EMAIL_FROM",       "QubitLogic <hello@qubitlogic.dev>")
SMTP_HOST    = os.getenv("SMTP_HOST",        "smtppro.zoho.eu")
SMTP_PORT    = int(os.getenv("SMTP_PORT",    "587"))
MAX_AGE_DAYS = int(os.getenv("MAX_POST_AGE_DAYS", "14"))
```

Then the script:

1. fetches the latest `<item>` from `RSS_URL`
2. compares the GUID with `STATE_PATH`
3. rejects stale posts older than `MAX_AGE_DAYS`
4. selects confirmed subscribers only
5. sends the email via SMTP
6. saves the GUID only if the run fully succeeds

The confirmed-subscriber rule is explicit:

```python
rows = con.execute(
    "SELECT email, unsub_token FROM subscribers WHERE confirmed=1"
).fetchall()
```

That single query is the key to preserving **double opt-in** all the way through the broadcast layer.

### Skip conditions built into the sender

| Condition | Why it skips |
|-----------|--------------|
| No RSS item | Nothing new to send |
| GUID already sent | Prevent duplicate weekly emails |
| Post older than `MAX_AGE_DAYS` | Avoid sending stale content |
| No confirmed subscribers | No active audience yet |
| Partial SMTP failures | GUID is not saved, so the next run can retry |

That is a better safety model than “always send latest post no matter what”.

---

## Step 2 — Keep RSS and environment predictable

The sender depends on one boring thing being true: **your RSS feed must exist and point at the live site**.

QubitLogic already exposes RSS from the homepage output. In `hugo.toml`:

```toml
[outputs]
  home = ["HTML", "RSS", "JSON"]
```

That produces:

- `/index.xml` for RSS
- `/index.json` for search

On the VPS, the workflow writes an `.env` file with the newsletter settings. The important lines are:

```ini
NEWSLETTER_DB=/var/lib/qubitlogic/newsletter.db
NEWSLETTER_STATE=/var/lib/qubitlogic/last_sent_guid.txt
SITE_URL=https://qubitlogic.dev
RSS_URL=https://qubitlogic.dev/index.xml
EMAIL_FROM="QubitLogic <hello@qubitlogic.dev>"
SMTP_HOST=smtppro.zoho.eu
SMTP_PORT=587
SMTP_USER=hello@qubitlogic.dev
SMTP_PASSWORD=your-app-password
```

Check the feed and environment manually:

```bash
curl -s https://yourdomain.dev/index.xml | rg "<title>|<item>"
set -a; source /opt/qubitlogic/newsletter/.env; set +a
python3 /opt/qubitlogic/newsletter/send.py --dry-run
```

Expected behaviour:

- RSS returns at least one `<item>`
- dry run logs the latest post
- no message is actually sent

If dry run says “No confirmed subscribers yet”, that is not a bug. It means your list is still empty or unconfirmed.

---

## Step 3 — Schedule Tuesday 09:00 UTC in `newsletter.yml`

QubitLogic schedules the weekly send with GitHub Actions:

```yaml
name: Newsletter

on:
  schedule:
    - cron: "0 9 * * 2"

  workflow_dispatch:
    inputs:
      mode:
        options:
          - dry-run
          - test-send
          - send
          - force-send
          - setup-api
```

The comment in the workflow is important:

```yaml
# Tuesday 09:00 UTC = 10:00 BST (Apr-Oct) / 09:00 GMT (Nov-Mar)
```

That means the human send time stays reasonable for UK readers even though the cron is stored in UTC.

### What each workflow mode is for

| Mode | Use it when |
|------|-------------|
| `dry-run` | You want to parse RSS and see what would happen |
| `test-send` | You want one copy delivered to a single address |
| `send` | Normal weekly broadcast |
| `force-send` | You deliberately want to resend the latest item |
| `setup-api` | First-time VPS install of service and Nginx wiring |

The workflow then SSHes to the VPS, loads `/opt/qubitlogic/newsletter/.env`, and runs the sender:

```bash
set -a; source /opt/qubitlogic/newsletter/.env; set +a
/opt/qubitlogic/newsletter/venv/bin/python \
  /opt/qubitlogic/newsletter/send.py
```

That is simple, auditable, and easy to reproduce manually when you need to debug a failed send.

---

## Step 4 — Why Monday publish / Tuesday send works well

QubitLogic publishes the article first, then sends the digest the next morning.

### The cadence

| Day | What happens |
|-----|--------------|
| Monday | Publish the new article |
| Monday afternoon/evening | Deploy completes, RSS updates, metadata settles |
| Tuesday 09:00 UTC | GitHub Actions runs the broadcast |

This timing has three benefits:

1. **RSS is definitely up to date** before the send starts
2. **last-minute article edits** do not trigger duplicate emails
3. the newsletter feels like a consistent weekly digest rather than an instant alert

It also matches the confirmation page in `newsletter/api.py`, which tells new subscribers: **“You'll receive the next tutorial on Tuesday morning.”**

### What happens if you publish late

| Publish time | Result |
|--------------|--------|
| Monday | Included in Tuesday send |
| Early Tuesday before cron | Usually included, but risky if deploy lags |
| Tuesday after cron | Waits until next scheduled run unless you trigger `force-send` |

For a one-person technical publication, that is a good trade-off. Predictability beats clever automation.

---

## Step 5 — Subscribe and confirm before testing the broadcast

Do this once with a real address before your first scheduled send.

### 1) Subscribe through the public endpoint

```bash
curl -i -X POST \
  -F "email=you@example.com" \
  -F "website=" \
  https://yourdomain.dev/api/newsletter/subscribe
```

The API will send a confirmation email. If you do not receive it, check spam first, then your SMTP configuration.

### 2) Click the confirmation link

The confirmation email points at:

```text
https://yourdomain.dev/api/newsletter/confirm?token=...
```

After clicking it, the row becomes active.

### 3) Verify the database row

```bash
sqlite3 /var/lib/qubitlogic/newsletter.db \
  "SELECT email, confirmed, created_at FROM subscribers ORDER BY created_at DESC;"
```

Expected result: your address appears with `confirmed = 1`.

### 4) Run a dry run

```bash
set -a; source /opt/qubitlogic/newsletter/.env; set +a
/opt/qubitlogic/newsletter/venv/bin/python \
  /opt/qubitlogic/newsletter/send.py --dry-run
```

Expected result:

- latest RSS item is logged
- your confirmed address appears in the “Would send to” output
- no email is actually sent

### 5) Run a single-address test send

If you want the full email formatting check before Tuesday, use:

```bash
set -a; source /opt/qubitlogic/newsletter/.env; set +a
/opt/qubitlogic/newsletter/venv/bin/python \
  /opt/qubitlogic/newsletter/test_send.py you@example.com
```

That is safer than blasting the whole list while you are still checking the subject line and template.

---

## Step 6 — Normal send, force-send, and recovery behaviour

When the real run happens, `newsletter/send.py` constructs both plain-text and HTML emails, sends them via SMTP, and tracks success counts.

Normal send:

```bash
set -a; source /opt/qubitlogic/newsletter/.env; set +a
/opt/qubitlogic/newsletter/venv/bin/python \
  /opt/qubitlogic/newsletter/send.py
```

Intentional resend:

```bash
set -a; source /opt/qubitlogic/newsletter/.env; set +a
/opt/qubitlogic/newsletter/venv/bin/python \
  /opt/qubitlogic/newsletter/send.py --force
```

The recovery rule is excellent for small lists:

- if all sends succeed, the script saves the latest GUID
- if any sends fail, the GUID is **not** saved

So the next run can retry instead of silently treating a partial failure as complete.

### Manual checks after a live send

```bash
cat /var/lib/qubitlogic/last_sent_guid.txt
sqlite3 /var/lib/qubitlogic/newsletter.db \
  "SELECT email, confirmed FROM subscribers WHERE confirmed=1;"
```

You should see:

- a non-empty GUID state file
- only confirmed rows in the active audience

---

## Verification checklist

Use these checks whenever you change the sender, workflow, or SMTP settings:

| Check | Command | Expected |
|-------|---------|----------|
| RSS is live | `curl -s https://yourdomain.dev/index.xml \| rg "<item>|<guid>"` | Latest post appears |
| API health | `curl -s http://127.0.0.1:8001/api/newsletter/health` | `{"ok": true}` |
| Subscriber confirmed | `sqlite3 /var/lib/qubitlogic/newsletter.db "SELECT email, confirmed FROM subscribers;"` | Test row shows `1` |
| Dry run works | `python3 /opt/qubitlogic/newsletter/send.py --dry-run` | Logs latest post and target count |
| State file updates after live send | `cat /var/lib/qubitlogic/last_sent_guid.txt` | Latest GUID stored |

If cron appears to do nothing, run the exact send command manually first. It is much faster to debug the script than to guess from the scheduler.

---

## Troubleshooting

**Dry run says “Already sent this post”** — The latest GUID matches `NEWSLETTER_STATE`. Use `--force` only if you intentionally want a resend.

**No confirmed subscribers yet** — You subscribed but did not click the confirmation email. Check the row in SQLite before blaming cron.

**Emails are not arriving** — Verify SMTP credentials, SPF, DKIM, and that your provider allows app passwords.

**Wrong article is sent** — The script always takes the latest item from `index.xml`. Check your publish dates and RSS ordering.

**Tuesday run skipped a new article** — It may have been published after the cron fired, or the deploy had not updated RSS yet. That is exactly why Monday publish / Tuesday send is the safer rhythm.

---

## Frequently Asked Questions

### Why does QubitLogic send the newsletter on Tuesday rather than immediately after publishing?

Because the editorial cadence is Monday publish, Tuesday send. Publishing on Monday gives the article time to deploy, enter RSS, and settle in Search Console and social previews; Tuesday 09:00 UTC then sends a clean weekly digest. That is simpler than sending instantly on every post and avoids bombarding subscribers during editing or same-day updates.

### Does `newsletter/send.py` email only confirmed subscribers?

Yes. The script queries `SELECT email, unsub_token FROM subscribers WHERE confirmed=1`, so pending sign-ups are ignored until the user clicks the confirmation link. That preserves the double opt-in flow from the API tutorial.

### How do I test the broadcast flow safely?

Subscribe with a real address, click the confirmation email, confirm the SQLite row shows `confirmed=1`, then run `python3 newsletter/send.py --dry-run` or use the GitHub Actions `test-send` mode. Dry run proves RSS parsing and subscriber selection without emailing the full list.

### What stops the same article being emailed twice?

QubitLogic stores the latest sent GUID in `NEWSLETTER_STATE` and compares it with the newest RSS item. A normal run skips if the GUID matches; `--force` overrides that check when you intentionally want to resend.

### Should I use Mailchimp, Beehiiv, or Listmonk instead?

If your newsletter is the product, Beehiiv or Listmonk may be worth it. If your site is primarily a technical blog and you want one weekly broadcast from your own RSS feed, `send.py` plus SQLite is far cheaper, easier to audit, and keeps subscriber data on your own VPS.

---

## Next steps

1. [Self-Hosted Newsletter API: FastAPI, SQLite, No Mailchimp](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/)
2. [Deploy Hugo to VPS: GitHub Actions & rsync](/infrastructure/deploy-hugo-github-actions-vps/)
3. [Hugo SEO: Sitemap, Schema & Search Console Setup](/infrastructure/hugo-seo-search-console-sitemap-schema/)
4. [How to Build a Technical Blog with Cursor and Hugo](/build-technical-blog-cursor-hugo/)

---

*Affiliate links may appear in partner boxes on this site. See [Affiliate Disclosure](/affiliate-disclosure/).*
