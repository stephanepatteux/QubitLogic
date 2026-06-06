---
title: "Cloudflare + Nginx on a VPS: Static Site & API"
date: 2026-06-06T13:00:00+01:00
lastmod: 2026-06-06T13:00:00+01:00
draft: false
description: "Put Cloudflare in front of your VPS — DNS proxy, Full (Strict) SSL with Origin CA, Nginx for Hugo static files plus FastAPI API routes, and cache rules that skip /api."
keywords:
  - "cloudflare nginx vps setup"
  - "cloudflare full strict origin certificate"
  - "hugo site cloudflare cdn"
  - "static site api subdomain nginx"
  - "cloudflare digitalocean tutorial"
summary: "The production edge for QubitLogic: orange-cloud DNS, Origin CA on Nginx, static Hugo at / and FastAPI behind /api — without Flexible SSL mistakes or redirect loops."
series: ["Phase 1: Infrastructure"]
tags: ["cloudflare", "nginx", "vps", "ssl", "hugo", "fastapi", "cdn", "dns", "infrastructure"]
categories: ["tutorial"]
images: ["/images/og/cloudflare-nginx-vps-static-site-api.png"]
weight: 6
ShowToc: true
TocOpen: false
faq:
  - q: "What is the difference between Cloudflare Flexible and Full (strict) SSL?"
    a: "Flexible encrypts traffic between the visitor and Cloudflare but sends plain HTTP to your origin — anyone on the path to your VPS can read it. Full (strict) encrypts end-to-end and requires a valid certificate on Nginx. Use Full (strict) with a Cloudflare Origin CA certificate — free, 15-year validity, issued in the dashboard."
  - q: "Why does Cloudflare cause redirect loops with Nginx?"
    a: "The classic loop: Cloudflare Flexible SSL hits your Nginx HTTP→HTTPS redirect, which redirects back, forever. Fix: set SSL mode to Full (strict), install an Origin CA cert on Nginx, and ensure Nginx listens on 443 with that certificate."
  - q: "Should I cache API routes behind Cloudflare?"
    a: "No. Create a Cache Rule to bypass cache when URI path starts with /api/. POST requests (newsletter subscribe) must never be cached — you will silently drop subscriptions or serve stale error responses."
howto_total_time: "PT1H"
howto_cost: "0"
howto_steps:
  - name: "Add domain to Cloudflare and update nameservers"
    text: "Create a free Cloudflare account, add your site, set the A record to proxied (orange cloud), and point registrar nameservers to Cloudflare."
  - name: "Set SSL to Full (strict)"
    text: "In SSL/TLS overview, select Full (strict) — never Flexible for a VPS with HTTPS Nginx."
  - name: "Install Origin CA certificate on Nginx"
    text: "Generate a 15-year Origin CA cert in the dashboard, save origin.pem and origin.key on the VPS under /etc/ssl/cloudflare/."
  - name: "Configure Nginx for static Hugo and API proxy"
    text: "Serve Hugo from root, proxy_pass /api/ to 127.0.0.1:8000, redirect HTTP to HTTPS."
  - name: "Add cache bypass rules for /api/"
    text: "Create a Cache Rule to bypass cache on /api/ paths and verify cf-cache-status on static vs API responses."
---

## Overview

A bare VPS exposes your IP and handles every DDoS byte itself. **Cloudflare's free plan** adds CDN caching, DNS, and edge TLS — while Nginx on the VPS serves your [Hugo](/infrastructure/deploy-hugo-github-actions-vps/) `public/` folder and proxies [FastAPI](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) on `/api/`.

This matches how **qubitlogic.dev** runs: domain at a registrar, nameservers at Cloudflare, origin on Ubuntu 24.04.

### Traffic flow

```
Visitor → Cloudflare edge (TLS, cache, DDoS)
       → Your VPS Nginx (Origin CA TLS)
       → /        → Hugo static files
       → /api/*   → FastAPI on 127.0.0.1:8000
```

Cloudflare's free tier includes unmetered DDoS mitigation, global CDN caching for static assets, and DNS — there is no reason to expose a bare VPS IP for a Hugo blog.

### SSL mode comparison

| Mode | Visitor → CF | CF → Origin | Use for VPS? |
|------|--------------|-------------|--------------|
| Off | HTTP | HTTP | Never |
| Flexible | HTTPS | **HTTP** | Never (insecure origin) |
| Full | HTTPS | HTTPS (any cert) | Risky |
| **Full (strict)** | HTTPS | HTTPS (valid origin cert) | **Yes** |

---

## Prerequisites

- [Hardened VPS](/infrastructure/secure-ubuntu-24-04-vps-hardening/)
- Hugo site built to `/var/www/yoursite/public/`
- FastAPI listening on `127.0.0.1:8000` ([deploy guide](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/))
- Domain you control (register at [Dynadot](https://www.dynadot.com/) — [Ambassador affiliate](https://www.dynadot.com/affiliate))

{{< affiliate_stack >}}

{{< affiliate_box
    name="Dynadot"
    url="AFFILIATE_LINK_DYNADOT"
    cta="Search domains"
    badge="Registrar"
    desc="Register your .dev or .com, then point nameservers to Cloudflare. WHOIS privacy included on most TLDs."
    price="Competitive renewals"
>}}

{{< callout type="info" title="Cloudflare Registrar" >}}
[Cloudflare Registrar](https://developers.cloudflare.com/registrar/) sells domains at cost — no markup, no affiliate programme. We use **Dynadot + Cloudflare DNS** when we want registrar affiliate revenue; use Cloudflare Registrar if you prefer one dashboard and at-cost renewals.
{{< /callout >}}

---

## Step 1 — Add site to Cloudflare

1. Create account at [cloudflare.com](https://www.cloudflare.com/)
2. **Add a site** → enter `yourdomain.dev`
3. Choose **Free** plan
4. Cloudflare scans DNS — confirm the **A record** → your VPS IP is **Proxied** (orange cloud)
5. Update nameservers at your registrar (Dynadot → Domain → Nameservers → Custom → paste Cloudflare NS)

Propagation: usually 15 minutes–24 hours. Docs: [Cloudflare DNS setup](https://developers.cloudflare.com/dns/zone-setups/full-setup/).

---

## Step 2 — SSL/TLS mode: Full (Strict)

Dashboard → **SSL/TLS** → Overview → **Full (strict)**.

| Mode | Problem |
|------|---------|
| Flexible | HTTPS to visitor, HTTP to origin — insecure |
| Full | Encrypted but accepts bad origin certs |
| **Full (strict)** | Requires valid cert on Nginx ✅ |

Reference: [Cloudflare SSL modes](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/).

---

## Step 3 — Origin CA certificate on Nginx

Dashboard → **SSL/TLS** → **Origin Server** → Create certificate (15-year, `yourdomain.dev` + `*.yourdomain.dev`).

On the VPS:

```bash
sudo mkdir -p /etc/ssl/cloudflare
sudo nano /etc/ssl/cloudflare/origin.pem      # paste certificate
sudo nano /etc/ssl/cloudflare/origin.key      # paste private key
sudo chmod 600 /etc/ssl/cloudflare/origin.key
```

Origin CA docs: [developers.cloudflare.com/ssl/origin-configuration/origin-ca](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/).

---

## Step 4 — Nginx: static Hugo + API proxy

```bash
sudo tee /etc/nginx/sites-available/yoursite > /dev/null <<'EOF'
server {
    listen 80;
    server_name yourdomain.dev www.yourdomain.dev;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.dev www.yourdomain.dev;

    ssl_certificate     /etc/ssl/cloudflare/origin.pem;
    ssl_certificate_key /etc/ssl/cloudflare/origin.key;

    root /var/www/yoursite/public;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ =404;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/yoursite /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Community walkthrough: [DigitalOcean — Cloudflare + Nginx on Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-host-a-website-using-cloudflare-and-nginx-on-ubuntu-22-04).

---

## Step 5 — Cache rules (don't cache API)

Dashboard → **Caching** → **Cache Rules**:

- **Bypass cache** when URI Path starts with `/api/`
- **Cache everything** for static assets (`*.css`, `*.js`, images) — optional

Newsletter `POST` must never be cached. See [self-hosted newsletter API](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/).

---

## Step 6 — Optional: lock origin to Cloudflare IPs

Advanced: restrict UFW so only [Cloudflare IP ranges](https://www.cloudflare.com/ips/) reach ports 80/443. **Keep SSH open** to your home IP or provider console.

This prevents attackers from bypassing the CDN if they discover your raw VPS IP. Trade-off: more firewall maintenance when Cloudflare updates ranges.

---

## Verification

```bash
curl -sI https://yourdomain.dev/ | head -5          # cf-cache-status, server: cloudflare
curl -s https://yourdomain.dev/api/health           # FastAPI JSON
curl -sI -X POST https://yourdomain.dev/api/newsletter/subscribe  # not cached
```

Browser: padlock → certificate issued by Cloudflare (edge), origin uses Origin CA.

---

## Troubleshooting

**Too many redirects** — Usually Flexible SSL + Nginx HTTPS redirect loop. Set **Full (strict)**.

**521 Web server down** — Nginx not running or firewall blocks Cloudflare. Check `sudo systemctl status nginx`.

**403 on static files** — Wrong `root` path or permissions: `sudo chown -R www-data:www-data /var/www/yoursite/public` (or `deploy` if you prefer).

---

## Next steps

1. [Hugo GitHub Actions deploy](/infrastructure/deploy-hugo-github-actions-vps/)
2. [Nginx hardening (rate limits)](/infrastructure/nginx-reverse-proxy-python-ai-api/)
3. [VPS benchmark comparison](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/)

---

*Affiliate links may appear in partner boxes. [Affiliate Disclosure](/affiliate-disclosure/).*
