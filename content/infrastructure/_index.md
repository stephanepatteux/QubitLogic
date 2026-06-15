---
title: "Infrastructure Tutorials — VPS, Nginx & Python"
description: "VPS provisioning, Ubuntu hardening, Nginx configuration, FastAPI deployment, and CI/CD pipelines for AI workloads. Self-hosted, benchmarked, production-ready."
keywords:
  - "VPS tutorials"
  - "Nginx Python deployment"
  - "Ubuntu server hardening"
  - "self-hosted AI infrastructure"
images: ["/images/og/infrastructure.png"]
---

Production infrastructure for solo developers and small teams — benchmarked on real VPS hardware, not marketing copy.

## Learning path

Follow these in order if you are building from scratch:

1. [Ubuntu 24.04 VPS Hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/) — SSH, UFW, Fail2Ban baseline
2. [Provision a VPS for AI workloads](/infrastructure/how-to-provision-vps-ai-agent-workloads/) — Python stack and benchmarks
3. [Deploy FastAPI on Ubuntu 24.04](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) — Gunicorn, systemd, Certbot
4. [Nginx reverse proxy hardening](/infrastructure/nginx-reverse-proxy-python-ai-api/) — rate limits, LLM timeouts
5. [Self-hosted newsletter API](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/) — FastAPI + SQLite + GDPR opt-in
6. [Cloudflare + Nginx](/infrastructure/cloudflare-nginx-vps-static-site-api/) — CDN, Origin CA, static + API
7. [Deploy Hugo via GitHub Actions](/infrastructure/deploy-hugo-github-actions-vps/) — rsync CI/CD
8. [Hetzner VPS provision](/infrastructure/hetzner-vps-provision-python-ai-ubuntu-24-04/) — EU price-performance path
9. [Uptime Kuma monitoring](/infrastructure/uptime-kuma-monitoring-ubuntu-vps-24-04/) — health checks for Hugo + API
10. [Hugo SEO & Search Console](/infrastructure/hugo-seo-search-console-sitemap-schema/) — sitemap, schema, GSC
11. [Newsletter broadcasts](/infrastructure/self-hosted-newsletter-broadcast-cron-rss/) — weekly RSS → SMTP
12. [VPS backup with Restic](/infrastructure/vps-backup-restore-restic-ubuntu-24-04/) — disaster recovery

Full table with benchmarks and advanced topics: [Start Here](/start-here/).

**Publishing cadence:** new infra tutorials publish **Mondays 08:00 UK**; newsletter sends **Tuesdays 09:00 UTC** (see [broadcast guide](/infrastructure/self-hosted-newsletter-broadcast-cron-rss/)).

## By topic

| Topic | Articles |
|-------|----------|
| Security | [Hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/), [Nginx hardening](/infrastructure/nginx-reverse-proxy-python-ai-api/) |
| Python APIs | [FastAPI deploy](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/), [Newsletter API](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/) |
| Static sites | [Hugo Actions deploy](/infrastructure/deploy-hugo-github-actions-vps/), [Build log](/build-technical-blog-cursor-hugo/) |
| Edge / CDN | [Cloudflare + Nginx](/infrastructure/cloudflare-nginx-vps-static-site-api/) |
| CI/CD | [Python pipeline](/infrastructure/cicd-pipeline-ai-python-scripts/), [Hugo deploy](/infrastructure/deploy-hugo-github-actions-vps/) |
| Provider choice | [DO vs Vultr](/infrastructure/digitalocean-vs-vultr-performance-benchmarks/), [DO vs Vultr vs Hetzner 2026](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/) |
