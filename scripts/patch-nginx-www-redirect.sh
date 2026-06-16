#!/usr/bin/env bash
# Idempotent: force www → apex redirects in /etc/nginx/sites-available/qubitlogic
set -euo pipefail

NGINX_CONF="/etc/nginx/sites-available/qubitlogic"

if [[ ! -f "$NGINX_CONF" ]]; then
  echo "Missing $NGINX_CONF" >&2
  exit 1
fi

if grep -q 'return 301 https://qubitlogic.dev\$request_uri;' "$NGINX_CONF" \
  && awk '/listen 443/,/^}/' "$NGINX_CONF" | grep -q 'server_name www.qubitlogic.dev;' \
  && awk '/server_name qubitlogic.dev;/,/^}/' "$NGINX_CONF" | grep -vq 'www.qubitlogic.dev'; then
  echo "Nginx www → apex redirect already configured"
  sudo nginx -t
  sudo systemctl reload nginx
  exit 0
fi

echo "Patching $NGINX_CONF for www → apex redirect..."

sudo python3 - "$NGINX_CONF" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text()

# HTTP: always send traffic to apex HTTPS
text = re.sub(
    r"(listen 80;\s*\n\s*server_name qubitlogic\.dev www\.qubitlogic\.dev;\s*\n\s*)return 301 https://\$host\$request_uri;",
    r"\1return 301 https://qubitlogic.dev$request_uri;",
    text,
    count=1,
)

www_ssl_block = """
server {
    listen 443 ssl http2;
    server_name www.qubitlogic.dev;

    ssl_certificate     /etc/letsencrypt/live/qubitlogic.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qubitlogic.dev/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    return 301 https://qubitlogic.dev$request_uri;
}
"""

if "server_name www.qubitlogic.dev;" not in text or "return 301 https://qubitlogic.dev$request_uri;" not in text:
    # Split combined apex+www SSL server into www redirect + apex content server
    pattern = re.compile(
        r"server \{\s*\n"
        r"(\s*listen 443[^\n]*;\s*\n)"
        r"\s*server_name qubitlogic\.dev www\.qubitlogic\.dev;\s*\n"
        r"(.*?\n)\}",
        re.DOTALL,
    )

    def split_ssl(match: re.Match[str]) -> str:
        listen_line = match.group(1)
        body = match.group(2)
        return (
            www_ssl_block.strip()
            + "\n\nserver {\n"
            + listen_line
            + "    server_name qubitlogic.dev;\n"
            + body
            + "}"
        )

    new_text, count = pattern.subn(split_ssl, text, count=1)
    if count:
        text = new_text
    elif "server_name qubitlogic.dev www.qubitlogic.dev;" in text:
        text = text.replace(
            "server_name qubitlogic.dev www.qubitlogic.dev;",
            "server_name qubitlogic.dev;",
            1,
        )
        if www_ssl_block.strip() not in text:
            text = text.replace(
                "server {\n    listen 443",
                www_ssl_block.strip() + "\n\nserver {\n    listen 443",
                1,
            )

path.write_text(text)
print("Nginx config patched")
PY

sudo nginx -t
sudo systemctl reload nginx
echo "Nginx reloaded — www now redirects to https://qubitlogic.dev"
