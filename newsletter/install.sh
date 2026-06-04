#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# QubitLogic Newsletter — one-shot VPS install
# Run as ubuntu on the VPS:  bash /tmp/newsletter/install.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="/opt/qubitlogic/newsletter"
DATA_DIR="/var/lib/qubitlogic"
CONFIG_DIR="/etc/qubitlogic"
SERVICE="qubitlogic-newsletter"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Creating directories..."
sudo mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$CONFIG_DIR"
sudo chown ubuntu:ubuntu "$DATA_DIR"

echo "==> Copying files..."
sudo cp "$SCRIPT_DIR/api.py"          "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/send.py"         "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
sudo chown -R ubuntu:ubuntu "$INSTALL_DIR"

echo "==> Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

echo "==> Writing env file template (edit with your SMTP credentials)..."
if [ ! -f "$CONFIG_DIR/newsletter.env" ]; then
sudo tee "$CONFIG_DIR/newsletter.env" > /dev/null <<'ENV'
# QubitLogic Newsletter — SMTP and runtime config
# Edit this file then: sudo systemctl restart qubitlogic-newsletter

NEWSLETTER_DB=/var/lib/qubitlogic/newsletter.db
NEWSLETTER_STATE=/var/lib/qubitlogic/last_sent_guid.txt
SITE_URL=https://qubitlogic.dev
RSS_URL=https://qubitlogic.dev/index.xml

EMAIL_FROM=QubitLogic <hello@qubitlogic.dev>
SMTP_HOST=smtppro.zoho.eu
SMTP_PORT=587
SMTP_USER=hello@qubitlogic.dev
SMTP_PASSWORD=CHANGE_ME
ENV
  sudo chmod 600 "$CONFIG_DIR/newsletter.env"
  echo "   ↳ Created $CONFIG_DIR/newsletter.env — set SMTP_PASSWORD before starting"
else
  echo "   ↳ $CONFIG_DIR/newsletter.env already exists — left unchanged"
fi

echo "==> Installing systemd service..."
sudo cp "$SCRIPT_DIR/qubitlogic-newsletter.service" \
    "/etc/systemd/system/${SERVICE}.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"
sudo systemctl restart "$SERVICE"
sleep 2
sudo systemctl is-active --quiet "$SERVICE" \
  && echo "   ↳ Service is running" \
  || echo "   ↳ WARNING: service not running — check: journalctl -u $SERVICE -n 30"

echo ""
echo "==> Add this location block to your Nginx config for qubitlogic.dev:"
echo "    (usually /etc/nginx/sites-available/qubitlogic)"
echo ""
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

echo ""
echo "==> After editing Nginx: sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "==> Edit SMTP_PASSWORD in $CONFIG_DIR/newsletter.env then:"
echo "    sudo systemctl restart $SERVICE"
echo ""
echo "==> Test dry-run:"
echo "    source $CONFIG_DIR/newsletter.env && python3 $INSTALL_DIR/send.py --dry-run"
echo ""
echo "Done."
