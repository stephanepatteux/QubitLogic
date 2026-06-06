---
title: "Uptime Kuma on Ubuntu 24.04: Monitor Your VPS Stack"
date: 2026-06-16T08:00:00+01:00
lastmod: 2026-06-16T08:00:00+01:00
draft: false
description: "Run Uptime Kuma on Ubuntu 24.04 with Docker Compose, put it behind Nginx, and monitor your Hugo site, FastAPI /health endpoint, and HTTPS certificate expiry from one self-hosted dashboard."
keywords:
  - "uptime kuma ubuntu 24.04"
  - "uptime kuma docker compose vps"
  - "monitor fastapi health endpoint"
  - "monitor hugo website ssl expiry"
  - "uptimerobot alternative self hosted"
  - "vps monitoring dashboard"
summary: "A hardened VPS still needs visibility. This guide runs Uptime Kuma on Ubuntu 24.04 with Docker Compose, keeps the dashboard off the public app port, and sets up checks for your Hugo front end, FastAPI health route, and SSL expiry."
series: ["Phase 1: Infrastructure"]
tags: ["uptime-kuma", "monitoring", "docker", "nginx", "ubuntu", "vps", "fastapi", "hugo", "infrastructure"]
categories: ["tutorial"]
images: ["/images/og/uptime-kuma-monitoring-ubuntu-vps-24-04.png"]
weight: 15
ShowToc: true
TocOpen: false
faq:
  - q: "Is Uptime Kuma a good alternative to UptimeRobot?"
    a: "Yes for many solo-developer stacks. Uptime Kuma gives you self-hosted monitors, status pages, SSL expiry checks, and notification integrations without a recurring SaaS fee. The trade-off is that you maintain the container yourself, so you own updates, backups, and availability of the monitoring node."
  - q: "Should I expose Uptime Kuma on port 3001 directly to the internet?"
    a: "No. Bind the container to 127.0.0.1:3001 and reverse proxy it through Nginx on a dedicated hostname such as status.example.com. That keeps the app off a raw public port and lets you reuse the same TLS and Cloudflare patterns as the rest of your VPS stack."
  - q: "What should I monitor on a Hugo plus FastAPI VPS?"
    a: "At minimum: the public Hugo homepage over HTTPS, the FastAPI /health endpoint, and certificate expiry on the hostname serving users. Those three checks cover content delivery, application liveness, and impending TLS failures."
  - q: "Can Uptime Kuma run on the same VPS it monitors?"
    a: "Yes, and that is perfectly reasonable for a small stack. Just remember the limitation: if the whole VPS is down, an on-box Uptime Kuma instance cannot alert you. For business-critical uptime, pair it with one external monitor as a second opinion."
  - q: "How do I update Uptime Kuma safely?"
    a: "From the compose directory, run docker compose pull and docker compose up -d. Back up the data volume first so you can roll back if a release changes the database schema or notification behaviour."
howto_total_time: "PT40M"
howto_cost: "0"
howto_steps:
  - name: "Install Docker Engine and the Compose plugin"
    text: "Add Docker's Ubuntu repository, install docker-ce plus docker-compose-plugin, and confirm the daemon is running."
  - name: "Launch Uptime Kuma with Docker Compose"
    text: "Create a compose.yaml file under /opt/uptime-kuma, bind the container to 127.0.0.1:3001, and start it with a persistent data directory."
  - name: "Publish the dashboard through Nginx"
    text: "Proxy status.example.com to 127.0.0.1:3001 instead of exposing port 3001 publicly, and protect the route with basic auth if desired."
  - name: "Add site, API, and TLS monitors"
    text: "Create monitors for your Hugo homepage, FastAPI /health endpoint, and SSL certificate expiry threshold in the Uptime Kuma UI."
  - name: "Back up, update, and verify alerts"
    text: "Archive the data directory, pull fresh container images, restart the stack, and test that checks transition cleanly between up and down states."
---

## Overview

Hardening a VPS is only half the job. Once the stack is live, you need to know whether:

- your **Hugo site** still answers over HTTPS
- your **FastAPI** app still returns a healthy response
- your **TLS certificate** is nearing expiry

That is exactly where **Uptime Kuma** fits. It gives you a self-hosted monitoring dashboard with HTTP checks, certificate expiry alerts, notifications, and optional status pages — all without paying an ongoing SaaS bill for a small personal stack.

This article runs Uptime Kuma on Ubuntu 24.04 with **Docker Compose**, keeps it on `127.0.0.1:3001`, and publishes it cleanly through Nginx. It fits neatly after [Ubuntu hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/), works alongside the [FastAPI deployment guide](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/), and can sit behind the same edge model described in the [Cloudflare + Nginx guide](/infrastructure/cloudflare-nginx-vps-static-site-api/).

### At a glance

| Item | Value |
|------|-------|
| Runtime | Docker Compose |
| Default local port | `127.0.0.1:3001` |
| Best public hostname | `status.example.com` |
| Monitors to add first | Hugo homepage, FastAPI `/health`, SSL expiry |
| Cost | £0 extra if you already have the VPS |
| Next | [Cloudflare + Nginx](/infrastructure/cloudflare-nginx-vps-static-site-api/) for a cleaner edge setup |

### How this guide compares

| Feature | UptimeRobot free / SaaS route | This guide |
|---------|-------------------------------|------------|
| Hosting model | Vendor-hosted | **Self-hosted on your VPS** |
| Recurring fee | Free tier limits, paid upgrades later | **No SaaS fee** |
| Data ownership | Stored with provider | **Stored on your box** |
| Custom dashboard URL | Vendor subdomain or paid options | **Your own subdomain** |
| SSL expiry checks | Yes | Yes |
| Maintenance burden | Low | **You update it and keep the backups** |
| Works with existing Nginx + Cloudflare setup | Indirectly | **Yes, same stack** |

If you want a set-and-forget external monitor, UptimeRobot is simpler. If you want **control, no monthly bill, and one more service inside your own stack**, Uptime Kuma is the better fit.

---

## Prerequisites

- Ubuntu 24.04 VPS with a sudo user such as `deploy`
- [Hardening complete](/infrastructure/secure-ubuntu-24-04-vps-hardening/) so only expected ports are public
- Nginx already present or available to install
- A hostname such as `status.example.com` if you want a clean dashboard URL
- A Hugo site and FastAPI app already reachable, ideally following the [FastAPI deployment guide](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/)

{{< affiliate_stack >}}

{{< callout type="info" title="One important limitation" >}}
Running Uptime Kuma on the same VPS it monitors is convenient, but it cannot alert you if the entire box disappears from the network. For critical production workloads, keep one external probe as well.
{{< /callout >}}

---

## Step 1 — Install Docker Engine and Compose

Install Docker from Docker's official Ubuntu repository rather than relying on the older distro package.

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

Add your user to the `docker` group, then start a fresh shell:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker version
docker compose version
```

If `newgrp docker` is awkward in your shell session, simply log out and back in before continuing.

---

## Step 2 — Launch Uptime Kuma with Docker Compose

Create a dedicated directory and a Compose file that binds the dashboard to localhost only.

```bash
sudo mkdir -p /opt/uptime-kuma
sudo chown -R "$USER":"$USER" /opt/uptime-kuma
cd /opt/uptime-kuma

tee compose.yaml > /dev/null <<'EOF'
services:
  uptime-kuma:
    image: louislam/uptime-kuma
    container_name: uptime-kuma
    restart: unless-stopped
    ports:
      - "127.0.0.1:3001:3001"
    volumes:
      - ./data:/app/data
EOF

docker compose up -d
docker compose ps
curl -I http://127.0.0.1:3001
```

Expected: the container is `Up`, and the local HTTP probe returns a `200`, `302`, or similar valid response from Uptime Kuma.

---

## Step 3 — Put the dashboard behind Nginx

Do not expose port `3001` directly. Reuse your normal reverse-proxy layer and give the dashboard its own hostname, for example `status.example.com`.

Optional basic auth is a sensible extra layer for an internal ops tool:

```bash
sudo apt install -y nginx apache2-utils
sudo htpasswd -bc /etc/nginx/.htpasswd statusadmin CHANGE_ME_STRONG_PASSWORD
```

Create the Nginx site:

```bash
sudo tee /etc/nginx/sites-available/uptime-kuma > /dev/null <<'EOF'
server {
    listen 80;
    server_name status.example.com;

    location / {
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/uptime-kuma /etc/nginx/sites-enabled/uptime-kuma
sudo nginx -t
sudo systemctl reload nginx
```

At this point you can either:

- terminate TLS directly on Nginx, following the [FastAPI deployment guide](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/), or
- place the hostname behind the same [Cloudflare + Nginx pattern](/infrastructure/cloudflare-nginx-vps-static-site-api/) you use for the public site

---

## Step 4 — Add monitors for Hugo, FastAPI, and SSL expiry

Before you create the monitors in the Uptime Kuma UI, verify each target from the shell.

Check the public Hugo site:

```bash
curl -I https://example.com/
```

Check the API health route:

```bash
curl -fsS https://api.example.com/health
```

Check certificate dates for the public hostname:

```bash
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | \
openssl x509 -noout -dates
```

Now open `https://status.example.com` and add:

1. **HTTP(s) monitor** for `https://example.com/`
2. **HTTP(s) monitor** for `https://api.example.com/health`
3. Enable **certificate expiry notification** on the HTTPS monitors, for example at **14 days**

For the API monitor, favour a short interval and ensure your `/health` route returns a simple `200 OK` quickly. The pattern from the [FastAPI deployment guide](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) is ideal for this.

---

## Step 5 — Back up and update the monitoring stack

You own this service, so treat it like any other app: back it up and update it deliberately.

Create a quick archive of the persistent data:

```bash
cd /opt/uptime-kuma
tar -czf "uptime-kuma-backup-$(date +%F).tar.gz" data
ls -lh uptime-kuma-backup-*.tar.gz
```

Update to the latest image:

```bash
cd /opt/uptime-kuma
docker compose pull
docker compose up -d
docker compose ps
```

If you use notifications, trigger a test alert from the Uptime Kuma UI after upgrades so you know webhooks, email, or chat integrations still work.

---

## Verification

Run these checks after setup:

| Check | Command | Expected |
|-------|---------|----------|
| Docker daemon | `systemctl is-active docker` | `active` |
| Kuma container | `cd /opt/uptime-kuma && docker compose ps` | `uptime-kuma` is `Up` |
| Local dashboard | `curl -I http://127.0.0.1:3001` | HTTP response from Kuma |
| Public dashboard proxy | `curl -I http://status.example.com` | Nginx response |
| Hugo target | `curl -I https://example.com/` | `200` or valid redirect chain |
| FastAPI health | `curl -fsS https://api.example.com/health` | JSON health payload |
| TLS dates | `echo \| openssl s_client -servername example.com -connect example.com:443 2>/dev/null \| openssl x509 -noout -dates` | Sensible `notAfter` date |

Inside the Uptime Kuma UI, make sure all three monitors go **green** and show the correct hostname.

---

## Common mistakes

- **Publishing `3001` publicly** instead of binding it to `127.0.0.1`
- **Forgetting to re-login after adding the user to the `docker` group**
- **Monitoring the wrong FastAPI URL**, such as a route requiring auth instead of a simple public `/health`
- **Assuming HTTPS expiry is a separate service** when the normal HTTPS monitor can already track it
- **Running only on-box monitoring** and forgetting that a full VPS outage will silence the monitor too

---

## Troubleshooting

**`docker compose` is not found** — Confirm `docker-compose-plugin` is installed, not just `docker.io`.

**The dashboard loads locally but not via Nginx** — Run `sudo nginx -t`, reload Nginx, and confirm the hostname resolves to the VPS IP.

**The WebSocket UI behaves oddly behind the proxy** — Re-check the `Upgrade` and `Connection "upgrade"` headers in the Nginx config.

**The API monitor shows down but the app seems fine** — Test the exact URL with `curl -fsS`. Many apps have `/docs` or `/` working while `/health` is missing or protected.

**No alerts arrive during an outage** — Send a test notification from Uptime Kuma and verify your notification integration after every major image update.

---

## Frequently Asked Questions

### Is Uptime Kuma a good alternative to UptimeRobot?

Yes for many solo-developer stacks. Uptime Kuma gives you self-hosted monitors, status pages, SSL expiry checks, and notification integrations without a recurring SaaS fee. The trade-off is that you maintain the container yourself, so you own updates, backups, and availability of the monitoring node.

### Should I expose Uptime Kuma on port 3001 directly to the internet?

No. Bind the container to `127.0.0.1:3001` and reverse proxy it through Nginx on a dedicated hostname such as `status.example.com`. That keeps the app off a raw public port and lets you reuse the same TLS and Cloudflare patterns as the rest of your VPS stack.

### What should I monitor on a Hugo plus FastAPI VPS?

At minimum: the public Hugo homepage over HTTPS, the FastAPI `/health` endpoint, and certificate expiry on the hostname serving users. Those three checks cover content delivery, application liveness, and impending TLS failures.

### Can Uptime Kuma run on the same VPS it monitors?

Yes, and that is perfectly reasonable for a small stack. Just remember the limitation: if the whole VPS is down, an on-box Uptime Kuma instance cannot alert you. For business-critical uptime, pair it with one external monitor as a second opinion.

### How do I update Uptime Kuma safely?

From the compose directory, run `docker compose pull` and `docker compose up -d`. Back up the data volume first so you can roll back if a release changes the database schema or notification behaviour.

---

## Next steps

1. [Ubuntu 24.04 VPS hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/) — make sure the monitoring host is locked down
2. [Deploy FastAPI on Ubuntu 24.04](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) — add a clean `/health` endpoint and production reverse proxy
3. [Cloudflare + Nginx on a VPS](/infrastructure/cloudflare-nginx-vps-static-site-api/) — place the dashboard and site behind the same edge pattern
4. [Deploy Hugo to VPS](/infrastructure/deploy-hugo-github-actions-vps/) — complete the static site side of the stack

---

*Affiliate links may appear in partner boxes on this site. See [Affiliate Disclosure](/affiliate-disclosure/).*
