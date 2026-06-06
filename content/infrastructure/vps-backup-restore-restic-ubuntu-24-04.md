---
title: "VPS Backup & Restore with Restic on Ubuntu 24.04"
date: 2026-07-07T08:00:00+01:00
lastmod: 2026-07-07T08:00:00+01:00
draft: false
description: "Back up and restore an Ubuntu 24.04 VPS with Restic, encrypted off-site storage, a daily systemd timer, and a real restore drill for /var/www, /opt/api, /var/lib/qubitlogic, Nginx sites, and SQLite databases."
keywords:
  - "restic ubuntu 24.04 backup"
  - "vps backup restore guide"
  - "restic s3 compatible backup"
  - "backblaze b2 restic ubuntu"
  - "sqlite backup restore vps"
  - "systemd timer restic"
summary: "Provider snapshots are useful for whole-server rollback, but they are not enough for portable, encrypted, file-level recovery. This guide shows how to back up a production Ubuntu 24.04 VPS with Restic and actually prove restore works."
series: ["Phase 1: Infrastructure"]
tags: ["restic", "backup", "restore", "ubuntu", "vps", "s3", "backblaze", "sqlite", "systemd", "infrastructure"]
categories: ["tutorial"]
images: ["/images/og/vps-backup-restore-restic-ubuntu-24-04.png"]
weight: 18
ShowToc: true
TocOpen: false
faq:
  - q: "Are provider snapshots enough for a small VPS?"
    a: "No. Provider snapshots are excellent for full-disk rollback after a bad package upgrade, but they are usually tied to one provider, one region, and one whole-volume restore flow. Restic adds encrypted, deduplicated, file-level backups you can restore to any Linux host."
  - q: "Can Restic safely back up SQLite databases?"
    a: "Yes, if you do it deliberately. For active SQLite files, create consistent copies with sqlite3 .backup before the Restic run, or briefly stop writers during the backup window. Blindly copying a busy SQLite file is how people discover corruption during restore instead of during backup."
  - q: "Should I use Backblaze B2 or generic S3-compatible object storage?"
    a: "Either works. For Restic, S3-compatible storage is the most flexible option because the same workflow covers Cloudflare R2, MinIO, Wasabi, Scaleway, and Backblaze B2's S3 API. B2 is often cost-effective for small backups; S3-compatible endpoints can be easier if you already standardise on AWS-style credentials."
  - q: "How often should I run a restore drill?"
    a: "At least monthly, and always after changing backup scope, retention, or application layout. A backup you have never restored is only a theory. Your drill should restore to a temporary directory, verify expected files exist, and run PRAGMA integrity_check on restored SQLite databases."
  - q: "What should I keep in Restic versus Git?"
    a: "Back up runtime data, configuration, and deploy artefacts: /var/www, /opt/api environment files, /var/lib/qubitlogic, and Nginx site configs. Git already stores your application source history, but it does not store server-side secrets, uploaded files, TLS material, logs, or live SQLite content."
howto_total_time: "PT50M"
howto_cost: "8"
howto_steps:
  - name: "Choose an off-site Restic repository"
    text: "Create an S3-compatible or Backblaze B2 bucket, store the repository password in a file, and initialise the Restic repo before you automate anything."
  - name: "Install Restic and define credentials"
    text: "Install restic and sqlite3, then write /etc/restic/restic.env with repository URL, password file, and object-storage credentials."
  - name: "Create a backup script for files and SQLite"
    text: "Back up /var/www, /opt/api, /var/lib/qubitlogic, and /etc/nginx site configs while creating consistent SQLite copies with sqlite3 .backup."
  - name: "Schedule a daily systemd timer"
    text: "Run the backup once per day with a persistent systemd timer so missed runs execute after reboot."
  - name: "Run the first backup and inspect snapshots"
    text: "Execute the service manually, check restic snapshots, and verify the timer is armed."
  - name: "Perform a restore drill"
    text: "Restore the latest snapshot to a temporary directory, verify required files, and run PRAGMA integrity_check on restored SQLite databases."
---

## Overview

If your VPS dies tonight, how long until you can bring back the blog, the API, Nginx config, and the SQLite data that powers your app? If the answer is “my provider has snapshots somewhere”, your recovery plan is incomplete.

**Restic** gives you encrypted, deduplicated, off-site backups with file-level restore. That matters when you need one Nginx vhost file, one SQLite database, or yesterday’s `/var/www` content — not a full disk rollback.

This guide assumes an Ubuntu 24.04 VPS already set up along the QubitLogic path:

- [Harden the VPS first](/infrastructure/secure-ubuntu-24-04-vps-hardening/)
- [Deploy Hugo to the server](/infrastructure/deploy-hugo-github-actions-vps/)
- [Run a self-hosted newsletter API with SQLite](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/)

The backup scope in this article covers:

- `/var/www` — Hugo output, uploads, static assets
- `/opt/api` — deployed app files, env files, scripts
- `/var/lib/qubitlogic` — runtime state and SQLite databases
- `/etc/nginx/sites-available` and `/etc/nginx/sites-enabled` — site configuration

### At a glance

| Item | Value |
|------|-------|
| Time | ~50 minutes |
| Cost | Object storage only; usually a few pounds/euros/dollars per month |
| Outcome | Encrypted off-site Restic backups + daily timer + tested restore drill |
| Best for | Single VPS running Hugo, FastAPI, SQLite, and Nginx |

### Provider snapshots vs Restic backups

| | DigitalOcean snapshots | Hetzner backups | **Restic (this guide)** |
|---|------------------------|-----------------|--------------------------|
| Granularity | Whole disk / volume | Whole server image | **File-level and directory-level** |
| Portability | Tied to provider | Tied to provider | **Restore anywhere Restic runs** |
| Encryption control | Provider-managed | Provider-managed | **End-to-end with your repository password** |
| Restore speed | Fast full rollback | Fast full rollback | Fast targeted restores; slower full rebuild |
| Best use | Failed upgrade, broken kernel, full-node rollback | “Undo the server” safety net | **Operational backups and real disaster recovery** |

The right answer is usually **both**: keep the provider safety net for whole-machine rollback, and keep Restic for portable, granular, encrypted recovery.

### How this guide compares

| Feature | “Just use snapshots” blog posts | Restic docs alone | This guide |
|---------|---------------------------------|-------------------|------------|
| Ubuntu 24.04 commands | Usually generic | Yes | **Yes** |
| Covers `/var/www`, `/opt/api`, `/var/lib/qubitlogic` | Rarely | No | **Yes** |
| Handles SQLite properly | Usually ignored | Partly | **Yes, with `.backup` copies** |
| Daily automation | Maybe cron | Manual examples | **systemd service + timer** |
| Restore drill | Often omitted | Basic | **Step-by-step verification** |

---

## Prerequisites

- Ubuntu 24.04 VPS with `sudo`
- Off-site object storage bucket:
  - S3-compatible storage such as Cloudflare R2, Wasabi, MinIO, or AWS S3
  - Or Backblaze B2, ideally via its S3-compatible API
- A long Restic repository password stored outside your shell history
- Optional provider snapshot/backups enabled for full-machine rollback

{{< affiliate_stack >}}

{{< callout type="warning" title="Backups are not complete until restore succeeds" >}}
Do not stop at `restic snapshots`. The minimum viable proof is: restore to a temporary directory, confirm key files exist, and run `PRAGMA integrity_check;` on restored SQLite databases.
{{< /callout >}}

---

## Step 1 — Create the Restic repository

Install the required packages:

```bash
sudo apt update
sudo apt install -y restic sqlite3
```

Create a directory for Restic configuration and a password file readable by root only:

```bash
sudo install -d -m 700 /etc/restic
sudo sh -c 'openssl rand -base64 48 > /etc/restic/password'
sudo chmod 600 /etc/restic/password
```

### Option A — S3-compatible storage

Create `/etc/restic/restic.env`:

```bash
sudo tee /etc/restic/restic.env > /dev/null <<'EOF'
RESTIC_REPOSITORY="s3:https://s3.eu-west-1.amazonaws.com/YOUR_BUCKET_NAME/restic"
RESTIC_PASSWORD_FILE="/etc/restic/password"
AWS_ACCESS_KEY_ID="REPLACE_ME"
AWS_SECRET_ACCESS_KEY="REPLACE_ME"
AWS_DEFAULT_REGION="eu-west-1"
EOF

sudo chmod 600 /etc/restic/restic.env
```

For non-AWS providers, replace the endpoint with the provider’s S3-compatible URL. Examples:

- Cloudflare R2: `s3:https://<ACCOUNT_ID>.r2.cloudflarestorage.com/YOUR_BUCKET_NAME/restic`
- Backblaze B2 S3 API: `s3:https://s3.eu-central-003.backblazeb2.com/YOUR_BUCKET_NAME/restic`
- MinIO: `s3:https://minio.example.com/YOUR_BUCKET_NAME/restic`

### Option B — Native Backblaze B2 backend

Restic supports B2 natively, although the project currently recommends the S3-compatible API for smoother behaviour and error handling. If you still want the native backend, use:

```bash
sudo tee /etc/restic/restic.env > /dev/null <<'EOF'
RESTIC_REPOSITORY="b2:YOUR_UNIQUE_BUCKET_NAME:restic"
RESTIC_PASSWORD_FILE="/etc/restic/password"
B2_ACCOUNT_ID="REPLACE_ME"
B2_ACCOUNT_KEY="REPLACE_ME"
EOF

sudo chmod 600 /etc/restic/restic.env
```

Initialise the repository:

```bash
sudo bash -lc 'set -a && source /etc/restic/restic.env && set +a && restic init'
```

Expected result: `created restic repository ...`

---

## Step 2 — Write a backup script for files and SQLite

The tricky part is **SQLite**. `restic backup /var/lib/qubitlogic` is fine for ordinary files, but an actively-written `.db` file can be inconsistent if you rely on raw file copy alone.

This script creates consistent SQLite copies first with `sqlite3 .backup`, then backs up:

- `/var/www`
- `/opt/api`
- `/var/lib/qubitlogic`
- `/etc/nginx/sites-available`
- `/etc/nginx/sites-enabled`

Create the script:

```bash
sudo tee /usr/local/bin/restic-vps-backup.sh > /dev/null <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

set -a
source /etc/restic/restic.env
set +a

STAMP="$(date +%F-%H%M%S)"
SQLITE_STAGE="/var/lib/qubitlogic/.restic-sqlite"
LOG_TAGS=(--tag vps --tag ubuntu-24.04 --tag daily)

rm -rf "$SQLITE_STAGE"
mkdir -p "$SQLITE_STAGE"
find /var/lib/qubitlogic \
  \( -path "$SQLITE_STAGE" -o -path "$SQLITE_STAGE/*" \) -prune -o \
  -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) -print0 |
while IFS= read -r -d '' db; do
  rel="${db#/var/lib/qubitlogic/}"
  out="$SQLITE_STAGE/${rel%.*}-$STAMP.sqlite3"
  mkdir -p "$(dirname "$out")"
  sqlite3 "$db" ".timeout 2000" ".backup '$out'"
done

restic backup \
  /var/www \
  /opt/api \
  /var/lib/qubitlogic \
  /etc/nginx/sites-available \
  /etc/nginx/sites-enabled \
  "${LOG_TAGS[@]}"

restic forget --keep-daily 7 --keep-weekly 5 --keep-monthly 12 --prune
EOF

sudo chmod 750 /usr/local/bin/restic-vps-backup.sh
```

### Why this script works

- `sqlite3 .backup` creates a transactionally consistent copy of each SQLite database
- The script recreates `.restic-sqlite/` on every run, so only fresh database copies are included
- `restic forget --prune` enforces a simple retention policy: 7 daily, 5 weekly, 12 monthly

{{< callout type="info" title="Busy write workloads" >}}
If your API writes to SQLite constantly, schedule the timer for a quiet period such as 03:17 and consider briefly stopping writers during backup. For most low-traffic blog/API setups, the online `.backup` approach is enough.
{{< /callout >}}

---

## Step 3 — Create a systemd service and daily timer

Use `systemd`, not ad-hoc cron, so you get clean logs, a proper service unit, and `Persistent=true` support after reboots.

Create the service:

```bash
sudo tee /etc/systemd/system/restic-vps-backup.service > /dev/null <<'EOF'
[Unit]
Description=Restic VPS backup
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/restic-vps-backup.sh
User=root
Group=root
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
EOF
```

Create the timer:

```bash
sudo tee /etc/systemd/system/restic-vps-backup.timer > /dev/null <<'EOF'
[Unit]
Description=Daily Restic VPS backup

[Timer]
OnCalendar=*-*-* 03:17:00
Persistent=true
RandomizedDelaySec=15m
Unit=restic-vps-backup.service

[Install]
WantedBy=timers.target
EOF
```

Enable and start the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now restic-vps-backup.timer
sudo systemctl list-timers restic-vps-backup.timer
```

Expected: `restic-vps-backup.timer` is listed with the next run time.

---

## Step 4 — Run the first backup manually

Do not wait until tomorrow to learn the configuration is wrong.

Run the service once now:

```bash
sudo systemctl start restic-vps-backup.service
sudo journalctl -u restic-vps-backup.service -n 100 --no-pager
```

Then inspect the repository:

```bash
sudo bash -lc 'set -a && source /etc/restic/restic.env && set +a && restic snapshots'
sudo bash -lc 'set -a && source /etc/restic/restic.env && set +a && restic stats latest'
```

You should see a fresh snapshot containing the expected paths and a non-zero size.

### Quick verification checklist

| Check | Command | Expected |
|-------|---------|----------|
| Timer enabled | `systemctl is-enabled restic-vps-backup.timer` | `enabled` |
| Last run logs | `sudo journalctl -u restic-vps-backup.service -n 50 --no-pager` | Completed backup output |
| Snapshot exists | `sudo bash -lc 'set -a && source /etc/restic/restic.env && set +a && restic snapshots'` | Latest snapshot listed |
| Nginx config included | `sudo bash -lc 'set -a && source /etc/restic/restic.env && set +a && restic ls latest /etc/nginx/sites-available'` | Your vhost files |
| SQLite copies included | `sudo bash -lc 'set -a && source /etc/restic/restic.env && set +a && restic find --glob "*.sqlite3"'` | Files under `.restic-sqlite/` |

---

## Step 5 — Perform a restore drill

This is the step most tutorials skip. Do it now, while the backup is still fresh in your mind.

Create a temporary restore target:

```bash
sudo rm -rf /root/restore-drill
sudo mkdir -p /root/restore-drill
```

Restore the latest snapshot:

```bash
sudo bash -lc 'set -a && source /etc/restic/restic.env && set +a && restic restore latest --target /root/restore-drill'
```

Verify the key paths exist:

```bash
sudo test -d /root/restore-drill/var/www && echo "/var/www restored"
sudo test -d /root/restore-drill/opt/api && echo "/opt/api restored"
sudo test -d /root/restore-drill/var/lib/qubitlogic && echo "/var/lib/qubitlogic restored"
sudo test -d /root/restore-drill/etc/nginx/sites-available && echo "nginx sites restored"
```

List restored SQLite copies:

```bash
sudo find /root/restore-drill/var/lib/qubitlogic/.restic-sqlite -type f
```

Run integrity checks on restored SQLite databases:

```bash
sudo find /root/restore-drill/var/lib/qubitlogic/.restic-sqlite -type f -name '*.sqlite3' -print0 |
while IFS= read -r -d '' db; do
  echo "Checking $db"
  sudo sqlite3 "$db" 'PRAGMA integrity_check;'
done
```

Expected output: `ok` for each database.

### How to restore into production

For a real incident, restore into a temporary directory first, compare, then copy back the needed paths:

```bash
sudo rsync -a /root/restore-drill/var/www/ /var/www/
sudo rsync -a /root/restore-drill/opt/api/ /opt/api/
sudo rsync -a /root/restore-drill/etc/nginx/sites-available/ /etc/nginx/sites-available/
sudo rsync -a /root/restore-drill/etc/nginx/sites-enabled/ /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

For SQLite, restore the checked copy from `.restic-sqlite/` into the live location during a maintenance window:

```bash
sudo cp /root/restore-drill/var/lib/qubitlogic/.restic-sqlite/app-2026-07-07-031700.sqlite3 /var/lib/qubitlogic/app.db
```

Replace the filename with the snapshot you actually restored.

---

## Step 6 — Add a simple restore runbook

Backups fail operationally when the process lives only in your head. Put a tiny runbook on the server:

```bash
sudo tee /root/RESTORE-NOTES.txt > /dev/null <<'EOF'
1. Load credentials from /etc/restic/restic.env
2. List snapshots: restic snapshots
3. Restore latest or chosen snapshot to /root/restore-drill
4. Verify /var/www, /opt/api, /var/lib/qubitlogic, and /etc/nginx/sites-available
5. Run sqlite3 PRAGMA integrity_check on restored .restic-sqlite copies
6. Rsync or copy the required paths back into production
7. Reload nginx and restart app services if needed
EOF

sudo chmod 600 /root/RESTORE-NOTES.txt
```

That file is not glamorous, but it is exactly what future-you wants at 02:00.

---

## Troubleshooting

**`Fatal: wrong password or no key found`** — Confirm `RESTIC_PASSWORD_FILE` points at the correct file and that you are targeting the right repository URL.

**S3-compatible storage returns region or signature errors** — Double-check the endpoint format and `AWS_DEFAULT_REGION`. Many S3-compatible providers need their exact regional endpoint.

**Timer never ran because the server was off** — `Persistent=true` means it should run on the next boot. Confirm with `systemctl status restic-vps-backup.timer`.

**SQLite integrity check fails during restore drill** — Stop writing services during backup, or narrow the backup window to a low-traffic period. Do not ignore a failed restore drill.

**The backup is larger than expected** — Check for logs, caches, or artefacts under `/opt/api` or `/var/lib/qubitlogic` that do not belong in backup scope. Excluding regenerable data can cut storage cost sharply.

---

## What Restic does not replace

- Provider snapshots for instant whole-VM rollback
- Git for application source history
- Database replication for higher-availability systems
- Infrastructure-as-code for rebuilding servers consistently

Restic is your **portable recovery layer**. It complements snapshots and deployment automation; it does not remove the need for them.

---

## Frequently Asked Questions

### Are provider snapshots enough for a small VPS?

No. Provider snapshots are great for full-disk rollback after a bad kernel or package update, but they are usually provider-specific and poor at targeted recovery. Restic gives you encrypted, file-level restore that works across providers.

### Can Restic safely back up SQLite databases?

Yes, if you create consistent copies first. The simplest reliable pattern is `sqlite3 .backup` into a staged directory immediately before the Restic snapshot, then verify those restored files with `PRAGMA integrity_check;`.

### Should I use Backblaze B2 or generic S3-compatible object storage?

Either is fine. If you want one workflow that also works with R2, Wasabi, MinIO, and AWS-style tools, use S3-compatible storage. Backblaze B2 is still a good fit, especially through its S3-compatible API.

### How often should I run a restore drill?

Monthly is the minimum for a production VPS, and immediately after changing backup scope, retention, or application layout. A restore drill should be routine, not an emergency-only ritual.

### What should I keep in Restic versus Git?

Git stores source code history. Restic stores what production actually needs to recover: secrets, `.env` files, uploaded assets, generated Hugo output, Nginx site config, and live SQLite data.

---

## Next steps

1. [Ubuntu 24.04 VPS hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/) — secure the box before relying on it
2. [Deploy Hugo to VPS with GitHub Actions and rsync](/infrastructure/deploy-hugo-github-actions-vps/) — repopulate `/var/www` predictably
3. [Self-hosted newsletter API with FastAPI and SQLite](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/) — a realistic workload to protect with Restic

---

*Affiliate links may appear in partner boxes on this site. See [Affiliate Disclosure](/affiliate-disclosure/).*
