---
title: "Nginx Reverse Proxy: Securing Your Python AI API"
date: 2026-06-01T11:00:00+01:00
lastmod: 2026-06-01T11:00:00+01:00
draft: false
description: "A production Nginx configuration for Python AI APIs — covering TLS termination via Certbot, rate limiting, upstream health checks, and proxy timeout tuning for slow LLM responses."
summary: "Uvicorn should never face the internet directly. This guide builds a hardened Nginx reverse proxy layer in front of your FastAPI AI backend — with TLS, rate limiting, and LLM-aware timeout tuning."

series: ["Phase 1: Infrastructure"]
tags: ["nginx", "linux", "python", "fastapi", "tls", "security", "ai-agents", "infrastructure"]
categories: ["tutorial"]

images: ["/images/og-default.png"]

weight: 2
---

## Overview

In [Part 1 of this series](/infrastructure/how-to-provision-vps-ai-agent-workloads/) we provisioned a hardened Ubuntu 24.04 VPS and ran uvicorn behind a basic Nginx proxy. That configuration is fine for local testing — it is not acceptable in production.

The problem is that `uvicorn` is an ASGI server, not a hardened web server. It has no built-in:

- TLS termination
- Rate limiting
- Request size enforcement
- HTTP/2 support
- Static file caching
- Access logging with structured output

Every Python AI API that talks to the internet needs a proper reverse proxy in front of it. Nginx is the right tool: battle-tested, memory-efficient, and capable of absorbing abuse before it reaches your Python process.

This guide builds that layer completely — including one Nginx behaviour that almost everyone gets wrong with LLM backends: **timeout configuration for slow inference responses.**

---

## Prerequisites

- A VPS provisioned from [Part 1](/infrastructure/how-to-provision-vps-ai-agent-workloads/)
- A domain name pointed at your VPS IP (`A` record)
- Nginx installed (`sudo apt install -y nginx`)
- Your FastAPI app running on `127.0.0.1:8000` via systemd

{{< callout type="info" title="No domain yet?" >}}
You can follow every step except the TLS section using your VPS IP address directly. Come back to the Certbot step once your domain's DNS has propagated.
{{< /callout >}}

{{< affiliate_box
    name="DigitalOcean"
    url="https://m.do.co/c/YOURREF"
    cta="Deploy a Droplet"
    badge="Recommended"
    desc="The fastest way to get a VPS with a static IP. Add a domain via the Networking tab and DigitalOcean manages your DNS records for free."
    price="From $6/mo"
>}}

---

## Step 1 — Directory Structure and Conventions

Nginx on Ubuntu uses the `sites-available` / `sites-enabled` pattern:

```
/etc/nginx/
├── nginx.conf                  ← global config (we tune this too)
├── sites-available/
│   └── myagent                 ← our config lives here
└── sites-enabled/
    └── myagent -> ../sites-available/myagent  ← symlink to activate
```

Check Nginx is running:

```bash
sudo systemctl status nginx
sudo nginx -v
# nginx version: nginx/1.24.0
```

---

## Step 2 — Tune the Global `nginx.conf`

Before writing our site config, fix two global defaults that affect AI API performance.

Open `/etc/nginx/nginx.conf`:

```bash
sudo nano /etc/nginx/nginx.conf
```

In the `http {}` block, set or confirm these values:

```nginx
http {
    # Match worker connections to your CPU core count
    worker_processes auto;

    # How long to keep idle keep-alive connections open
    keepalive_timeout 65;

    # Reject requests larger than 10 MB (prevents payload abuse)
    client_max_body_size 10M;

    # Buffer tuning — important for streaming LLM responses
    proxy_buffering        off;   # disable for SSE / streaming endpoints
    proxy_buffer_size      4k;
    proxy_buffers          8 4k;

    # Hide Nginx version from error pages
    server_tokens off;

    # Gzip for JSON responses
    gzip on;
    gzip_types application/json text/plain text/css application/javascript;
    gzip_min_length 1024;

    include /etc/nginx/sites-enabled/*;
}
```

{{< callout type="warning" title="proxy_buffering and streaming" >}}
If your AI API streams tokens via **Server-Sent Events (SSE)** or chunked transfer, you **must** set `proxy_buffering off` on that location block. With buffering on, Nginx holds the entire response in memory before forwarding it — your client sees nothing until the LLM finishes.
{{< /callout >}}

---

## Step 3 — Write the Site Config

Create `/etc/nginx/sites-available/myagent`:

```bash
sudo nano /etc/nginx/sites-available/myagent
```

```nginx
# ── Rate limiting zones (defined outside server block) ──────────────────────
# Zone: 10 MB shared memory, 20 requests/second per IP
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;

# Zone for stricter auth endpoints
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;


# ── HTTP → HTTPS redirect ────────────────────────────────────────────────────
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    # Allow Certbot ACME challenge through
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}


# ── Main HTTPS server ────────────────────────────────────────────────────────
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # ── TLS (Certbot fills these paths) ─────────────────────────────────────
    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    # ── Security headers ─────────────────────────────────────────────────────
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options           "DENY" always;
    add_header X-Content-Type-Options    "nosniff" always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy        "geolocation=(), microphone=(), camera=()" always;

    # ── Logging ──────────────────────────────────────────────────────────────
    access_log /var/log/nginx/myagent_access.log combined;
    error_log  /var/log/nginx/myagent_error.log warn;

    # ── Health check endpoint (no rate limit, no auth) ───────────────────────
    location = /health {
        proxy_pass         http://127.0.0.1:8000/health;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        access_log off;
    }

    # ── Auth endpoints — strict rate limit ───────────────────────────────────
    location ~ ^/api/v[0-9]+/auth {
        limit_req zone=auth_limit burst=3 nodelay;
        limit_req_status 429;

        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    # ── Streaming / SSE endpoints — buffering off ────────────────────────────
    location ~ ^/api/v[0-9]+/stream {
        limit_req zone=api_limit burst=10 nodelay;
        limit_req_status 429;

        proxy_pass             http://127.0.0.1:8000;
        proxy_http_version     1.1;
        proxy_set_header       Connection         "";
        proxy_set_header       Host               $host;
        proxy_set_header       X-Real-IP          $remote_addr;
        proxy_set_header       X-Forwarded-For    $proxy_add_x_forwarded_for;
        proxy_set_header       X-Forwarded-Proto  $scheme;

        # Critical for SSE
        proxy_buffering        off;
        proxy_cache            off;
        proxy_read_timeout     300s;   # 5 min — long LLM streams
        proxy_send_timeout     300s;
        chunked_transfer_encoding on;
    }

    # ── All other API routes ─────────────────────────────────────────────────
    location / {
        limit_req zone=api_limit burst=30 nodelay;
        limit_req_status 429;

        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade           $http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # LLM-aware timeouts — standard inference can take 30-90s
        proxy_connect_timeout  10s;
        proxy_send_timeout     120s;
        proxy_read_timeout     120s;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/myagent /etc/nginx/sites-enabled/
sudo nginx -t   # must print "syntax is ok"
sudo systemctl reload nginx
```

---

## Step 4 — TLS with Certbot (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx

sudo certbot --nginx \
    -d yourdomain.com \
    -d www.yourdomain.com \
    --agree-tos \
    --email you@youremail.com \
    --redirect
```

Certbot will:
1. Verify domain ownership via the ACME HTTP challenge
2. Install the certificate
3. Rewrite the Nginx config to point at the cert files
4. Add a systemd timer for automatic renewal

Verify the renewal timer is active:

```bash
sudo systemctl list-timers | grep certbot
# certbot.timer  Mon 2026-06-01 ...  active
```

Test your TLS grade: paste your domain into [SSL Labs](https://www.ssllabs.com/ssltest/) — the config above achieves **A+**.

---

## Step 5 — Rate Limiting Explained

The config uses two zones:

| Zone | Limit | Burst | Used for |
|---|---|---|---|
| `api_limit` | 20 req/s per IP | 30 | General API endpoints |
| `auth_limit` | 5 req/min per IP | 3 | Login / token endpoints |

**What `burst` means:** a client can exceed the rate limit momentarily up to `burst` requests, but excess requests beyond that receive a `429 Too Many Requests` immediately (`nodelay` means no queuing — reject fast).

To test your rate limiting is working:

```bash
# Install Apache Bench
sudo apt install -y apache2-utils

# Fire 50 rapid requests
ab -n 50 -c 10 https://yourdomain.com/api/v1/ping
```

You should see a mix of `200` and `429` responses in the output.

---

## Step 6 — Upstream Health Checks

Add a `/health` endpoint to your FastAPI app so Nginx (and future load balancers) can probe it:

```python
# main.py
from fastapi import FastAPI
import time

app = FastAPI()

START_TIME = time.time()

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME),
    }
```

Poll it manually:

```bash
curl -s https://yourdomain.com/health | python3 -m json.tool
# {
#     "status": "ok",
#     "uptime_seconds": 3842
# }
```

For a simple automated check via cron (alerts you if the API goes down):

```bash
crontab -e
```

```cron
*/5 * * * * curl -sf https://yourdomain.com/health || echo "API DOWN $(date)" >> /var/log/agent-health.log
```

---

## Step 7 — Proxy Timeout Tuning for LLM Backends

This is the setting most guides omit. Default Nginx `proxy_read_timeout` is **60 seconds**. GPT-4o generating a 2,000-token response can take 45–80 seconds on a loaded endpoint. Claude processing a large document can exceed 90 seconds.

If `proxy_read_timeout` fires before the LLM responds, Nginx returns a **502 Bad Gateway** — and your client has no idea why.

Our config sets:

```nginx
proxy_read_timeout 120s;   # standard inference endpoints
proxy_read_timeout 300s;   # streaming endpoints
```

Rule of thumb:

| Use case | Recommended `proxy_read_timeout` |
|---|---|
| Simple classification / short completions | 30s |
| Standard GPT-4o / Claude Sonnet calls | 120s |
| Large document processing | 180s |
| Streaming token output (SSE) | 300s |

{{< callout type="tip" title="Test your actual p99 latency" >}}
Before setting timeouts, measure your real LLM response times. In Python: wrap your API call in `time.perf_counter()` and log the result. Set `proxy_read_timeout` to at least 2× your observed p99. Don't guess.
{{< /callout >}}

---

## Step 8 — Benchmark: Before and After Nginx

Using `wrk` to simulate 50 concurrent users against the API:

```bash
sudo apt install -y wrk

# Before Nginx (direct uvicorn — DO NOT do this in production)
wrk -t4 -c50 -d30s http://127.0.0.1:8000/health

# After Nginx (HTTPS via proxy)
wrk -t4 -c50 -d30s https://yourdomain.com/health
```

{{< code_benchmark title="Nginx proxy overhead — wrk, 4 threads, 50 connections, 30s, Ubuntu 24.04 / 2 vCPU" >}}
| Metric | Direct uvicorn | Via Nginx |
|---|---|---|
| Requests/sec | 9,840 | 9,210 |
| Latency avg (ms) | 5.1 | 5.4 |
| Latency p99 (ms) | 18.2 | 19.7 |
| Proxy overhead | — | ~6% |
| TLS | No | Yes |
| Rate limiting | No | Yes |
| Security headers | No | Yes |
{{< /code_benchmark >}}

The Nginx overhead is **~6% throughput, ~0.3 ms latency** — completely negligible. You get TLS, rate limiting, and security headers for free at that cost.

---

## Conclusion

A properly configured Nginx reverse proxy is not optional for a production AI API. The key decisions from this guide:

1. **Global `nginx.conf` tuning** — disable proxy buffering for streaming endpoints before you need it.
2. **Separate location blocks** — auth endpoints get stricter rate limits than regular API routes.
3. **`proxy_read_timeout 120s` minimum** — the most commonly misconfigured value for LLM backends. Default 60s will cause intermittent 502s on heavy inference calls.
4. **Let's Encrypt via Certbot** — free, automatic, A+ grade. No excuse not to use it.
5. **Health endpoint** — expose `/health` and poll it. Know before your users do when the API is down.

The next article covers **optimising your Python environment performance on Ubuntu 24.04** — virtual environment isolation, `pip` dependency pinning, and `uvicorn` worker count tuning for CPU-bound vs. I/O-bound agent workloads.
