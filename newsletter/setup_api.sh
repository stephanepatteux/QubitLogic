#!/usr/bin/env bash
# Idempotent newsletter API setup on the VPS (systemd + Nginx + health check).
# Invoked by deploy.yml and newsletter.yml setup-api mode.
set -euo pipefail

INSTALL_DIR="/opt/qubitlogic/newsletter"
DATA_DIR="/var/lib/qubitlogic"
NGINX_CONF="/etc/nginx/sites-available/qubitlogic"
SERVICE="qubitlogic-newsletter"

echo "==> Ensuring directories and venv..."
sudo mkdir -p "$INSTALL_DIR" "$DATA_DIR"
sudo chown -R ubuntu:ubuntu "$INSTALL_DIR" "$DATA_DIR"

if [ ! -f "$INSTALL_DIR/venv/bin/python" ]; then
  python3 -m venv "$INSTALL_DIR/venv"
fi
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade \
  fastapi "uvicorn[standard]" python-multipart 2>/dev/null || true

if [ -n "${SMTP_PASSWORD:-}" ] && [ ! -f "$INSTALL_DIR/.env" ]; then
  echo "==> Writing .env (first install only)..."
  cat >"$INSTALL_DIR/.env" <<EOF
NEWSLETTER_DB=/var/lib/qubitlogic/newsletter.db
NEWSLETTER_STATE=/var/lib/qubitlogic/last_sent_guid.txt
SITE_URL=https://qubitlogic.dev
RSS_URL=https://qubitlogic.dev/index.xml
EMAIL_FROM="QubitLogic <hello@qubitlogic.dev>"
SMTP_HOST=smtppro.zoho.eu
SMTP_PORT=587
SMTP_USER=hello@qubitlogic.dev
SMTP_PASSWORD=${SMTP_PASSWORD}
EOF
  chmod 600 "$INSTALL_DIR/.env"
elif [ -f "$INSTALL_DIR/.env" ]; then
  echo "==> .env already present — left unchanged"
fi

echo "==> Installing systemd service..."
free_port_8001() {
  sudo systemctl stop "$SERVICE" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    if ! ss -tln | grep -q ':8001 '; then
      return 0
    fi
    sudo fuser -k 8001/tcp 2>/dev/null || true
    sleep 1
  done
  if ss -tln | grep -q ':8001 '; then
    echo "Port 8001 still in use:"
    ss -tlnp | grep ':8001 ' || true
    return 1
  fi
}

sudo cp "$INSTALL_DIR/qubitlogic-newsletter.service" \
  "/etc/systemd/system/${SERVICE}.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"

free_port_8001
sudo systemctl start "$SERVICE"
sleep 3

if ! sudo systemctl is-active --quiet "$SERVICE"; then
  echo "Service start failed — retrying after port cleanup..."
  free_port_8001
  sudo systemctl start "$SERVICE"
  sleep 3
fi

if sudo systemctl is-active --quiet "$SERVICE"; then
  echo "Service: running"
else
  echo "Service: FAILED — journalctl output:"
  sudo journalctl -xeu "$SERVICE" --no-pager -n 40
  exit 1
fi

newsletter_block() {
  cat <<'NGINX'
    # Newsletter API
    location /api/newsletter/ {
        proxy_pass         http://127.0.0.1:8001/api/newsletter/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 10s;
    }
NGINX
}

echo "==> Patching Nginx (HTTPS server block)..."
if awk '/listen 443/,/^}/' "$NGINX_CONF" | grep -q 'api/newsletter'; then
  echo "Nginx: /api/newsletter/ already in SSL server block — skipping insert"
else
  # Remove misplaced blocks outside the 443 server (e.g. accidental insert in :80 block)
  if grep -q 'api/newsletter' "$NGINX_CONF"; then
    echo "Nginx: removing misplaced /api/newsletter/ block(s)..."
    sudo python3 - <<'PY'
from pathlib import Path
import re

path = Path("/etc/nginx/sites-available/qubitlogic")
text = path.read_text()
text = re.sub(
    r"\n?    # Newsletter API\n    location /api/newsletter/ \{.*?\n    \}\n",
    "\n",
    text,
    flags=re.DOTALL,
)
path.write_text(text)
PY
  fi

  tmp="$(mktemp)"
  newsletter_block >"$tmp"
  sudo python3 - "$tmp" <<'PY'
import sys
from pathlib import Path

block = Path(sys.argv[1]).read_text()
path = Path("/etc/nginx/sites-available/qubitlogic")
lines = path.read_text().splitlines(keepends=True)
out = []
in_ssl = False
inserted = False
ssl_depth = 0

for line in lines:
    if not in_ssl and "listen 443" in line:
        in_ssl = True
        ssl_depth = 0
    if in_ssl:
        if "{" in line:
            ssl_depth += line.count("{")
        if "}" in line:
            ssl_depth -= line.count("}")
        if not inserted and line.strip() == "location / {":
            out.append(block)
            if not block.endswith("\n"):
                out.append("\n")
            inserted = True
        if ssl_depth <= 0 and "}" in line:
            in_ssl = False
    out.append(line)

if not inserted:
    raise SystemExit("Could not find 'location / {' in SSL server block")

path.write_text("".join(out))
PY
  rm -f "$tmp"
  sudo nginx -t
  sudo systemctl reload nginx
  echo "Nginx: reloaded with /api/newsletter/ in SSL server block"
fi

echo "==> Health check..."
curl -sf http://127.0.0.1:8001/api/newsletter/health && echo "API health: OK" || {
  echo "API health: FAILED"
  exit 1
}

if [ -f "$INSTALL_DIR/seed_subscriber.py" ]; then
  "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/seed_subscriber.py" \
    stephanepatteux@gmail.com || true
fi

echo "==> setup_api.sh complete"
