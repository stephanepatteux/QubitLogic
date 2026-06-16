#!/usr/bin/env bash
# Sync newsletter scripts to VPS, refresh .env, seed owner subscriber, send if new post.
# Called from deploy.yml / scheduled-deploy.yml / newsletter.yml (via SSH from GitHub Actions).
set -euo pipefail

VPS_HOST="${VPS_HOST:-ubuntu@51.195.86.197}"
SSH_OPTS="-o StrictHostKeyChecking=no"

if [[ -z "${SMTP_PASSWORD:-}" ]]; then
  echo "SMTP_PASSWORD is required" >&2
  exit 1
fi

ssh $SSH_OPTS "$VPS_HOST" 'bash -s' <<'SETUP'
set -e
sudo mkdir -p /opt/qubitlogic/newsletter /var/lib/qubitlogic
sudo chown -R ubuntu:ubuntu /opt/qubitlogic /var/lib/qubitlogic
if [ ! -f /opt/qubitlogic/newsletter/venv/bin/python ]; then
  python3 -m venv /opt/qubitlogic/newsletter/venv
fi
SETUP

rsync -avz -e "ssh $SSH_OPTS" newsletter/ "$VPS_HOST:/opt/qubitlogic/newsletter/"

ssh $SSH_OPTS "$VPS_HOST" "python3 - '$SMTP_PASSWORD'" <<'PYEOF'
import os, sys
password = sys.argv[1]
env = [
    "NEWSLETTER_DB=/var/lib/qubitlogic/newsletter.db",
    "NEWSLETTER_STATE=/var/lib/qubitlogic/last_sent_guid.txt",
    "SITE_URL=https://qubitlogic.dev",
    "RSS_URL=https://qubitlogic.dev/index.xml",
    'EMAIL_FROM="QubitLogic <hello@qubitlogic.dev>"',
    "SMTP_HOST=smtppro.zoho.eu",
    "SMTP_PORT=587",
    "SMTP_USER=hello@qubitlogic.dev",
    f"SMTP_PASSWORD={password}",
]
path = "/opt/qubitlogic/newsletter/.env"
with open(path, "w") as f:
    f.write("\n".join(env) + "\n")
os.chmod(path, 0o600)
print(f"Wrote {path}")
PYEOF

ssh $SSH_OPTS "$VPS_HOST" 'bash -s' <<'RUN'
set -e
set -a; source /opt/qubitlogic/newsletter/.env; set +a
/opt/qubitlogic/newsletter/venv/bin/python \
  /opt/qubitlogic/newsletter/seed_subscriber.py stephanepatteux@gmail.com
/opt/qubitlogic/newsletter/venv/bin/python \
  /opt/qubitlogic/newsletter/send.py
RUN
