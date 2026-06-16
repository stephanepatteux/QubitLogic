# Deployment Notes — QubitLogic on Ubuntu VPS + Nginx

## Architecture

| Component | Location |
|---|---|
| Static site (Hugo) | `/var/www/qubitlogic/` on VPS |
| Newsletter API (FastAPI) | `/opt/qubitlogic/newsletter/` on VPS, port 8001 |
| Newsletter DB | `/var/lib/qubitlogic/newsletter.db` (SQLite) |
| Env / secrets | `/opt/qubitlogic/newsletter/.env` (written by GitHub Actions) |
| VPS IP | `51.195.86.197` |

## GitHub Actions workflows

### `deploy.yml` — triggered on every push to `main`
1. Builds the Hugo site (`hugo --minify`)
2. Rsyncs `public/` → `/var/www/qubitlogic/`
3. Rsyncs `newsletter/` → `/opt/qubitlogic/newsletter/`
4. Seeds `stephanepatteux@gmail.com` as a **confirmed** subscriber (idempotent via `seed_subscriber.py`)

### `scheduled-deploy.yml` — Mondays 07:05 UTC
Publishes **future-dated** Hugo posts (`buildFuture = false`). New infra articles use `date: Monday 08:00 Europe/London`; this workflow runs after that time so they appear without a manual push.

### `newsletter.yml` — Tuesday 09:00 UTC + manual dispatch
Modes (select via `workflow_dispatch`):

| Mode | What it does |
|---|---|
| `dry-run` | Parse RSS, log what would be sent — no emails |
| `test-send` | Send latest post to a single address (default: stephanepatteux@gmail.com) |
| `send` | Normal weekly send — skips if post already sent this week |
| `force-send` | Send even if post was already sent |
| `setup-api` | One-time: install systemd service + patch Nginx |

## Required GitHub Secrets

| Secret | Description |
|---|---|
| `VPS_SSH_KEY` | Private key for `ubuntu@51.195.86.197` |
| `SMTP_PASSWORD` | Zoho Mail app password for `hello@qubitlogic.dev` |

### Optional secrets

| Secret | Description |
|---|---|
| `GOOGLE_SITE_VERIFICATION` | Meta tag content from [Google Search Console](https://search.google.com/search-console) → HTML tag verification. Injected at build time; also paste into `hugo.toml` `params.analytics.google.SiteVerificationTag` if preferred. |

Add at: **repo → Settings → Secrets and variables → Actions**.

## Google Search Console (recommended)

1. Add property `https://qubitlogic.dev` in Search Console.
2. Choose **HTML tag** verification and copy the `content="..."` value.
3. Either set GitHub secret `GOOGLE_SITE_VERIFICATION`, or paste the value in `hugo.toml` under `params.analytics.google.SiteVerificationTag`.
4. Push to `main`, then click **Verify** in Search Console.
5. Submit sitemap: `https://qubitlogic.dev/sitemap.xml`.
6. Optional: URL Inspection → `https://qubitlogic.dev/series/` → **Request removal** (taxonomy pages are `noindex` + blocked in `robots.txt`).

### Common Search Console coverage fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| **Not found (404)** | Indexed pages link to future-dated Hugo posts (`buildFuture = false`) | Only link from live pages after publish date; redeploy on Mondays or push to `main` |
| **Duplicate without user-selected canonical** | `www.qubitlogic.dev` serves same HTML as apex | Nginx 301: `www` → `https://qubitlogic.dev` (see nginx config above) |
| **Crawled – currently not indexed** on `/search/` or `/page/N/` | Utility/pagination pages were indexable | `noindex` + `robots.txt` Disallow (handled in `seo.html`) |
| **Duplicate robots meta** | PaperMod `head.html` and `seo.html` both emitted robots | Single robots tag in `seo.html` only |

## One-time VPS setup

Run `setup-api` workflow mode once after first deploy. It:
- Installs `qubitlogic-newsletter.service` as a systemd unit
- Kills any zombie on port 8001 before starting
- Patches `/etc/nginx/sites-available/qubitlogic` with the `/api/newsletter/` proxy block
- Seeds `stephanepatteux@gmail.com` as confirmed (weekly send test list)

**Weekly cadence:** publish articles **Monday 08:00 UK** → newsletter sends **Tuesday 09:00 UTC** (reads RSS `index.xml`).
- Reloads Nginx
- Health-checks the API

## Nginx site config (`/etc/nginx/sites-available/qubitlogic`)

```nginx
server {
    listen 80;
    server_name qubitlogic.dev www.qubitlogic.dev;
    return 301 https://qubitlogic.dev$request_uri;
}

server {
    listen 443 ssl http2;
    server_name www.qubitlogic.dev;

    ssl_certificate     /etc/letsencrypt/live/qubitlogic.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qubitlogic.dev/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    return 301 https://qubitlogic.dev$request_uri;
}

server {
    listen 443 ssl http2;
    server_name qubitlogic.dev;

    root /var/www/qubitlogic;
    index index.html;

    ssl_certificate     /etc/letsencrypt/live/qubitlogic.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qubitlogic.dev/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    add_header X-Frame-Options         "SAMEORIGIN"   always;
    add_header X-Content-Type-Options  "nosniff"      always;
    add_header Referrer-Policy         "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location ~* \.(css|js|woff2?|ttf|eot|svg|png|jpg|webp|ico)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location ~* \.html$ {
        expires -1;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml application/xml+rss text/javascript
               image/svg+xml;
    gzip_min_length 1024;
    gzip_comp_level 6;

    # Newsletter API
    location /api/newsletter/ {
        proxy_pass         http://127.0.0.1:8001/api/newsletter/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 10s;
    }

    location / {
        try_files $uri $uri/ $uri.html =404;
    }

    error_page 404 /404.html;
}
```

## TLS via Certbot

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d qubitlogic.dev -d www.qubitlogic.dev
```

Certbot adds a systemd timer for auto-renewal. Verify:

```bash
systemctl list-timers | grep certbot
```

## Newsletter service management

```bash
# Status
sudo systemctl status qubitlogic-newsletter

# Logs (live)
sudo journalctl -fu qubitlogic-newsletter

# Restart
sudo systemctl restart qubitlogic-newsletter

# Subscriber list
sqlite3 /var/lib/qubitlogic/newsletter.db \
  "SELECT email, confirmed, created_at FROM subscribers ORDER BY created_at DESC"
```

## Hugo version

Pinned at **v0.162.1 Extended** in `deploy.yml`.
