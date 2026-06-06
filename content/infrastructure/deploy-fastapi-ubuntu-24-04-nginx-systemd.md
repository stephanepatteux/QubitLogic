---
title: "Deploy FastAPI on Ubuntu 24.04: Nginx, systemd, SSL"
date: 2026-06-05T11:00:00+01:00
lastmod: 2026-06-06T08:00:00+01:00
draft: false
description: "Deploy FastAPI on Ubuntu 24.04 for production — Gunicorn + Uvicorn workers, systemd auto-restart, Nginx reverse proxy, Certbot HTTPS, and UFW. Step-by-step with verification."
keywords:
  - "deploy fastapi ubuntu 24.04"
  - "fastapi production vps"
  - "systemd fastapi service"
  - "nginx fastapi reverse proxy"
  - "gunicorn uvicorn workers"
  - "certbot nginx ssl"
summary: "Turn a local FastAPI app into a live HTTPS API on your VPS — without exposing uvicorn directly to the internet. The on-ramp to our advanced Nginx hardening guide."
series: ["Phase 1: Infrastructure"]
tags: ["fastapi", "python", "nginx", "systemd", "ubuntu", "vps", "ssl", "devops", "infrastructure"]
categories: ["tutorial"]
images: ["/images/og/deploy-fastapi-ubuntu-24-04-nginx-systemd.png"]
weight: 3
ShowToc: true
TocOpen: false
faq:
  - q: "Should I run uvicorn or Gunicorn in production?"
    a: "Run Gunicorn as the process manager with UvicornWorker (-k uvicorn.workers.UvicornWorker). Uvicorn alone is fine for development; Gunicorn gives you multiple workers, graceful restarts, and production-grade signal handling. Bind to 127.0.0.1:8000 and let Nginx handle TLS on 443."
  - q: "Why bind FastAPI to 127.0.0.1 instead of 0.0.0.0?"
    a: "Binding to localhost means only Nginx on the same machine can reach your app. UFW should not expose port 8000 publicly — attackers who bypass Nginx cannot hit uvicorn directly. This is the standard pattern in the official FastAPI deployment docs."
  - q: "How many Gunicorn workers do I need on a 1 GB VPS?"
    a: "Start with 2 workers (-w 2). Each Uvicorn worker loads your Python app into memory, so 4 workers on 1 GB RAM often causes OOM kills. Scale workers with RAM: roughly one worker per 512 MB–1 GB for lightweight APIs."
  - q: "Can I use the same VPS for Hugo and FastAPI?"
    a: "Yes — this is the QubitLogic pattern. Nginx serves Hugo static files at / and proxies /api/ to FastAPI on 127.0.0.1:8000. One Gunicorn service handles all API routes (newsletter, webhooks, health). See the Cloudflare + Nginx guide for the combined server block."
  - q: "Do I need Docker to deploy FastAPI on Ubuntu?"
    a: "No. On a single $6–12/mo VPS, systemd + Gunicorn is simpler than Docker: fewer moving parts, lower RAM overhead, and easier debugging with journalctl. Docker makes sense at multi-service scale; for one API on one VPS, native systemd is the right default."
howto_total_time: "PT45M"
howto_cost: "6"
howto_steps:
  - name: "Create sample FastAPI app and venv"
    text: "Install fastapi, uvicorn, and gunicorn in /opt/api, write a health endpoint, and verify with curl on 127.0.0.1:8000."
  - name: "Configure systemd service"
    text: "Create fastapi.service running Gunicorn with UvicornWorker, bound to 127.0.0.1:8000, with Restart=always."
  - name: "Set up Nginx reverse proxy"
    text: "Install Nginx, proxy_pass to 127.0.0.1:8000, set X-Forwarded-* headers, and test with nginx -t."
  - name: "Obtain Let's Encrypt certificate"
    text: "Run certbot --nginx for your API subdomain and verify HTTPS with curl."
  - name: "Confirm firewall and reboot test"
    text: "Ensure UFW allows only 22/80/443, port 8000 is not public, and the service survives reboot."
---

## Overview

Running `uvicorn main:app --reload` on your laptop is development. Production means **Gunicorn managing Uvicorn workers**, **systemd** restarting on crash, **Nginx** terminating TLS, and **Let's Encrypt** for free HTTPS.

This is the standard pattern used across DEV tutorials and the [FastAPI deployment docs](https://fastapi.tiangolo.com/deployment/) — adapted for a $6–12/mo VPS and the QubitLogic stack (newsletter API, webhooks, small agent backends).

**Before you start:** [Harden Ubuntu 24.04](/infrastructure/secure-ubuntu-24-04-vps-hardening/) on your server. For rate limiting and LLM timeout tuning, continue to [Nginx reverse proxy hardening](/infrastructure/nginx-reverse-proxy-python-ai-api/) after this guide.

### At a glance

| Layer | Component | Port | Faces internet? |
|-------|-----------|------|-----------------|
| Edge | Nginx + Certbot | 443 | Yes (TLS termination) |
| App | Gunicorn + Uvicorn | 8000 on 127.0.0.1 | No |
| Process | systemd | — | Auto-restart on crash |

This three-layer stack is what most DEV tutorials and the [FastAPI deployment guide](https://fastapi.tiangolo.com/deployment/) recommend for a single VPS. You get HTTPS, process supervision, and zero extra infrastructure cost.

### Gunicorn vs raw uvicorn

| | Development | Production |
|---|-------------|------------|
| Command | `uvicorn main:app --reload` | `gunicorn main:app -k uvicorn.workers.UvicornWorker` |
| Workers | 1 | 2+ (scale with RAM) |
| Bind address | `127.0.0.1` or `0.0.0.0` | **127.0.0.1 only** |
| TLS | None | Nginx + Certbot |

### How this guide compares

| Feature | Vultr / HostMyCode tutorials | RamNode guide | This guide |
|---------|------------------------------|---------------|--------------|
| Gunicorn + UvicornWorker | Partial | Yes | Yes |
| systemd service | Yes | Yes | Yes |
| Certbot HTTPS | Yes | Yes | Yes |
| Worker sizing for 1 GB RAM | Rare | Generic formula | **RAM table + OOM diagnostics** |
| Hugo + API on same VPS | No | No | **Yes** (path routing) |
| LLM timeout tuning | No | 300s in Nginx | Links to [dedicated Nginx guide](/infrastructure/nginx-reverse-proxy-python-ai-api/) |
| Full series path | Standalone | Standalone | [Hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/) → deploy → [newsletter](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/) |

Most provider tutorials stop at "hello world on HTTPS." This article is the on-ramp to a **complete QubitLogic-style stack** on one $6–12/mo VPS.

---

## Prerequisites

- Ubuntu 24.04 VPS with a `deploy` sudo user
- Domain `api.example.com` (or `example.com`) with an **A record** → VPS IP
- Sample FastAPI app (we provide a minimal one below)

{{< affiliate_stack >}}

{{< affiliate_box
    name="Cursor"
    url="AFFILIATE_LINK_CURSOR"
    cta="Try Cursor free"
    badge="Build the API"
    desc="Write and refactor your FastAPI routes in Cursor before deploying — same workflow we use for QubitLogic."
    offer="AI-assisted IDE"
>}}

---

## Step 1 — Sample application

On the server:

```bash
sudo mkdir -p /opt/api
sudo chown deploy:deploy /opt/api
cd /opt/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi "uvicorn[standard]" gunicorn
```

Create `main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Production API", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(payload: dict):
    return {"received": True, "keys": list(payload.keys())}
```

Test locally on the server:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
# another shell: curl -s http://127.0.0.1:8000/health
```

---

## Step 2 — systemd service (Gunicorn + UvicornWorker)

```bash
sudo tee /etc/systemd/system/fastapi.service > /dev/null <<'EOF'
[Unit]
Description=FastAPI (Gunicorn + Uvicorn)
After=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/opt/api
Environment="PATH=/opt/api/.venv/bin"
ExecStart=/opt/api/.venv/bin/gunicorn main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 2 \
  -b 127.0.0.1:8000 \
  --access-logfile - \
  --error-logfile -
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now fastapi
sudo systemctl status fastapi
```

Gunicorn design: [docs.gunicorn.org](https://docs.gunicorn.org/en/stable/design.html).

### How many workers?

Gunicorn's classic formula is `(2 × CPU cores) + 1`, but on a memory-constrained VPS the limit is usually **RAM per worker**, not CPU.

| VPS RAM | Suggested `-w` | Notes |
|---------|----------------|-------|
| 1 GB | 2 | Default for this guide; leave headroom for Nginx + OS |
| 2 GB | 2–3 | Fine for newsletter/webhook APIs |
| 4 GB | 3–5 | Add workers only after checking `free -h` under load |

Check memory after deploy:

```bash
ps aux --sort=-%mem | head -8
free -h
```

If you see OOM kills in `dmesg | grep -i oom`, reduce workers or add swap (see [hardening guide](/infrastructure/secure-ubuntu-24-04-vps-hardening/)).

For **I/O-bound** routes (LLM API calls, external HTTP), workers spend time waiting — you can often run more workers than the CPU formula suggests. For **CPU-bound** work (embedding models, pandas), stick to 1 worker per vCPU. See [Python environment tuning](/infrastructure/optimizing-python-environment-ubuntu-24-04/) for uvloop and preload options.

### Environment variables in production

When you add a `.env` file (newsletter SMTP, API keys), load it via systemd instead of hardcoding secrets:

```ini
EnvironmentFile=/opt/api/.env
```

Create `/opt/api/.env` owned by `deploy` with mode `600`. Never commit `.env` to Git — use the same pattern in [CI/CD deploy](/infrastructure/cicd-pipeline-ai-python-scripts/) with GitHub Secrets.

---

## Step 3 — Nginx reverse proxy

```bash
sudo apt install -y nginx
sudo tee /etc/nginx/sites-available/fastapi > /dev/null <<'EOF'
server {
    listen 80;
    server_name api.example.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 75s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    # WebSocket support (optional — enable if your API uses WS)
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Replace `api.example.com` with your domain. Nginx proxy module: [nginx.org docs](https://nginx.org/en/docs/http/ngx_http_proxy_module.html).

### Subdomain vs path on the same domain

Two valid patterns:

| Pattern | `server_name` | When to use |
|---------|---------------|-------------|
| **Subdomain** | `api.example.com` | Separate TLS cert, clear API boundary |
| **Path** | `example.com` + `location /api/` | Hugo blog + API on one cert (QubitLogic) |

If Hugo already serves `example.com`, add a `location /api/` block to that server — do not create a second Nginx site on port 80 for the same hostname. The [newsletter API guide](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/) uses the path pattern.

The `X-Forwarded-Proto` header matters when you later put [Cloudflare](/infrastructure/cloudflare-nginx-vps-static-site-api/) in front: FastAPI's `request.url` and redirect logic depend on it.

`proxy_read_timeout 120s` prevents 504 errors on slow routes (LLM calls, webhooks). Default Nginx timeout is 60s — too short for AI backends. For heavy inference, see [Nginx hardening](/infrastructure/nginx-reverse-proxy-python-ai-api/) (300s+).

### Zero-downtime code updates

After changing Python code:

```bash
cd /opt/api && source .venv/bin/activate && pip install -r requirements.txt  # if deps changed
sudo systemctl reload fastapi   # or restart if you changed systemd unit
```

Gunicorn gracefully replaces workers on `reload`. For breaking schema changes, test on `127.0.0.1:8000` before reloading.

---

## Step 4 — HTTPS with Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com --non-interactive --agree-tos -m you@example.com
```

Certbot auto-renews via systemd timer. Verify: [eff.org/certbot](https://certbot.eff.org/instructions).

```bash
curl -sI https://api.example.com/health
```

---

## Step 5 — Firewall reminder

If you followed the [hardening guide](/infrastructure/secure-ubuntu-24-04-vps-hardening/), ports 80/443 are already open. **Do not** expose port 8000 publicly — only Nginx should face the internet.

```bash
sudo ufw status
```

---

## Verification

| Test | Command | Expected |
|------|---------|----------|
| Service running | `systemctl is-active fastapi` | `active` |
| Local upstream | `curl -s http://127.0.0.1:8000/health` | `{"status":"ok"}` |
| Public HTTPS | `curl -s https://api.example.com/health` | `{"status":"ok"}` |
| Survives reboot | `sudo reboot` then curl again | still `ok` |

---

## Common mistakes

1. **Binding to `0.0.0.0:8000` and opening UFW port 8000** — bypasses Nginx TLS and rate limits. Always bind `127.0.0.1` and keep 8000 off the firewall.

2. **Running uvicorn directly in production** — no multi-worker support, weaker signal handling on deploy/restart. Use Gunicorn + UvicornWorker.

3. **Forgetting `WorkingDirectory` in systemd** — imports break if the service starts from `/` and cannot find `main.py`.

4. **Missing `proxy_set_header Host`** — some FastAPI middleware and OAuth redirects generate wrong URLs.

5. **Deploying before DNS propagates** — Certbot fails with "connection refused" or "NXDOMAIN". Wait for `dig +short api.example.com` to return your VPS IP.

6. **No health endpoint** — you cannot distinguish Nginx misconfig from app crash. Always expose `GET /health` and monitor it.

7. **Blocking calls inside `async def`** — freezes all workers under load. Use `async` HTTP clients or offload CPU work to a thread pool. Covered in depth in [Python tuning](/infrastructure/optimizing-python-environment-ubuntu-24-04/).

---

## Troubleshooting

**502 Bad Gateway** — Nginx cannot reach upstream.

```bash
sudo systemctl status fastapi
curl -s http://127.0.0.1:8000/health
journalctl -u fastapi -n 50 --no-pager
```

Common causes: service crashed, wrong bind address, or venv path changed after `pip install`.

**502 only on HTTPS, HTTP works** — Certbot modified Nginx config incorrectly. Compare `/etc/nginx/sites-enabled/fastapi` and run `sudo nginx -t`.

**Certbot fails** — DNS not propagated (`dig +short api.example.com`), port 80 blocked by UFW, or Cloudflare orange-cloud proxying before origin is ready. For Cloudflare, use [Full (strict)](/infrastructure/cloudflare-nginx-vps-static-site-api/) with Origin CA instead of Certbot on the origin.

**Service starts then dies** — syntax error in `main.py` or missing dependency:

```bash
cd /opt/api && source .venv/bin/activate
gunicorn main:app -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
```

Run in foreground to see the traceback.

**Slow LLM routes / 504 Gateway Timeout** — default Nginx `proxy_read_timeout` is 60s. LLM calls often need 120–300s. See [LLM-aware Nginx hardening](/infrastructure/nginx-reverse-proxy-python-ai-api/).

**High memory after deploy** — too many Gunicorn workers. Drop `-w` to 2 and add swap on 1 GB instances.

---

## Frequently Asked Questions

### Should I run uvicorn or Gunicorn in production?

Run Gunicorn as the process manager with `UvicornWorker` (`-k uvicorn.workers.UvicornWorker`). Uvicorn alone is fine for development; Gunicorn gives you multiple workers, graceful restarts, and production-grade signal handling. Bind to `127.0.0.1:8000` and let Nginx handle TLS on 443.

### Why bind FastAPI to 127.0.0.1 instead of 0.0.0.0?

Binding to localhost means only Nginx on the same machine can reach your app. UFW should not expose port 8000 publicly — attackers who bypass Nginx cannot hit uvicorn directly. This is the standard pattern in the [official FastAPI deployment docs](https://fastapi.tiangolo.com/deployment/).

### How many Gunicorn workers do I need on a 1 GB VPS?

Start with 2 workers (`-w 2`). Each Uvicorn worker loads your Python app into memory, so 4 workers on 1 GB RAM often causes OOM kills. Scale workers with RAM: roughly one worker per 512 MB–1 GB for lightweight APIs.

### Can I use the same VPS for Hugo and FastAPI?

Yes — this is the QubitLogic pattern. Nginx serves Hugo static files at `/` and proxies `/api/` to FastAPI on `127.0.0.1:8000`. One Gunicorn service handles all API routes.

### Do I need Docker to deploy FastAPI on Ubuntu?

No. On a single $6–12/mo VPS, systemd + Gunicorn is simpler than Docker: fewer moving parts, lower RAM overhead, and easier debugging with `journalctl`.

---

## Next steps

1. [Self-hosted newsletter API](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/) — real FastAPI workload on this stack
2. [Cloudflare + static site + API](/infrastructure/cloudflare-nginx-vps-static-site-api/)
3. [CI/CD deploy on git push](/infrastructure/cicd-pipeline-ai-python-scripts/)
4. [Python environment tuning](/infrastructure/optimizing-python-environment-ubuntu-24-04/)

---

*Affiliate links may appear in partner boxes. [Affiliate Disclosure](/affiliate-disclosure/).*
