---
title: "Deploy Hugo to VPS: GitHub Actions & rsync"
date: 2026-06-06T14:00:00+01:00
lastmod: 2026-06-06T14:00:00+01:00
draft: false
description: "Automate Hugo deploys to your VPS — GitHub Actions builds with submodules, rsync pushes public/ to Nginx docroot, and optional GOOGLE_SITE_VERIFICATION at build time."
keywords:
  - "deploy hugo site github actions vps"
  - "hugo rsync deploy nginx"
  - "github actions hugo workflow"
  - "papermod deploy ubuntu"
  - "hugo extended github actions"
summary: "Push to main → Hugo builds in CI → rsync to /var/www. The Hugo-specific complement to our Python CI/CD guide and the full QubitLogic build log."
series: ["Phase 1: Infrastructure"]
tags: ["hugo", "github-actions", "rsync", "nginx", "ci-cd", "devops", "papermod", "infrastructure"]
categories: ["tutorial"]
images: ["/images/og/deploy-hugo-github-actions-vps.png"]
weight: 7
ShowToc: true
TocOpen: false
faq:
  - q: "Why rsync instead of git pull on the VPS?"
    a: "The VPS only needs static HTML — not your Git history, Hugo binary, or theme source. rsync pushes the built public/ folder in seconds and avoids installing Hugo on production. git pull on the server couples deploy to server tooling and makes rollbacks harder."
  - q: "Why do I need submodules: recursive in GitHub Actions?"
    a: "PaperMod and most Hugo themes are Git submodules. Without recursive checkout, CI builds with an empty themes/ folder — you get an unstyled site. Always set submodules: recursive in actions/checkout."
  - q: "Is rsync --delete safe for Hugo deploys?"
    a: "Yes, when DEPLOY_PATH points at your Nginx docroot (e.g. /var/www/yoursite/public/). --delete removes stale files from old builds. Dry-run first with rsync -avzn if you are nervous — a wrong path can delete unrelated directories."
howto_total_time: "PT1H"
howto_cost: "0"
howto_steps:
  - name: "Prepare VPS docroot"
    text: "Create /var/www/yoursite/public owned by deploy, with Nginx root pointing at it."
  - name: "Add GitHub Actions secrets"
    text: "Store DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY, and DEPLOY_PATH as repository secrets."
  - name: "Create deploy.yml workflow"
    text: "Checkout with submodules, build Hugo extended with --minify, rsync public/ to the VPS."
  - name: "Set correct baseURL in hugo.toml"
    text: "Match baseURL to your production domain — wrong values break CSS and sitemap URLs."
  - name: "Push to main and verify"
    text: "Confirm Actions passes, curl the live site, and check google-site-verification if configured."
---

## Overview

Manually SSHing to run `git pull && hugo` works once. It fails when you forget submodules, ship a broken `baseURL`, or overwrite production during a bad build.

**GitHub Actions** builds Hugo in a clean environment, runs `hugo --minify`, and **rsync**s only the `public/` folder to your VPS. Nginx serves the files — no Node runtime on the server.

This is the deploy half of [How to Build a Technical Blog with Cursor and Hugo](/build-technical-blog-cursor-hugo/). For Python services on the same VPS, see [CI/CD for AI Python scripts](/infrastructure/cicd-pipeline-ai-python-scripts/).

### CI vs manual deploy

| | `ssh` + `hugo` on VPS | GitHub Actions + rsync |
|---|----------------------|------------------------|
| Hugo on server | Required | Not needed |
| Reproducible builds | No (server drift) | Yes (clean runner) |
| Submodule handling | Manual | Automatic |
| Rollback | Git revert on server | Re-run previous workflow |
| Cost | $0 | $0 (public repos) |

---

## Prerequisites

- Hugo site with theme submodule (e.g. [PaperMod](https://github.com/adityatelange/hugo-PaperMod))
- [Hardened VPS](/infrastructure/secure-ubuntu-24-04-vps-hardening/) with Nginx docroot at `/var/www/yoursite/public`
- GitHub repo with Actions enabled

{{< affiliate_stack >}}

{{< affiliate_box
    name="Cursor"
    url="AFFILIATE_LINK_CURSOR"
    cta="Try Cursor free"
    badge="Author in Cursor"
    desc="Edit Markdown and Hugo templates locally, push to GitHub, let Actions deploy — the QubitLogic workflow."
>}}

---

## Step 1 — Server directory layout

On the VPS:

```bash
sudo mkdir -p /var/www/yoursite/public
sudo chown -R deploy:deploy /var/www/yoursite
```

Nginx `root` points at `/var/www/yoursite/public` (see [Cloudflare + Nginx guide](/infrastructure/cloudflare-nginx-vps-static-site-api/)).

---

## Step 2 — GitHub secrets

Repository → **Settings** → **Secrets and variables** → **Actions**:

| Secret | Example |
|--------|---------|
| `DEPLOY_HOST` | `51.195.86.197` |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_KEY` | Private SSH key (ed25519) |
| `DEPLOY_PATH` | `/var/www/yoursite/public/` |
| `GOOGLE_SITE_VERIFICATION` | Optional — meta tag for Search Console |

Add the matching **public** key to `~deploy/.ssh/authorized_keys`.

---

## Step 3 — Workflow file

`.github/workflows/deploy.yml`:

```yaml
name: Deploy to VPS

on:
  push:
    branches: [main]

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
          fetch-depth: 0

      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: "0.162.1"
          extended: true

      - name: Build
        env:
          GOOGLE_SITE_VERIFICATION: ${{ secrets.GOOGLE_SITE_VERIFICATION }}
        run: hugo --minify

      - name: Rsync to VPS
        uses: burnett01/rsync-deployments@7.0.1
        with:
          switches: -avzr --delete
          path: public/
          remote_path: ${{ secrets.DEPLOY_PATH }}
          remote_host: ${{ secrets.DEPLOY_HOST }}
          remote_user: ${{ secrets.DEPLOY_USER }}
          remote_key: ${{ secrets.DEPLOY_KEY }}
```

Hugo hosting docs: [gohugo.io/hosting-and-deployment](https://gohugo.io/hosting-and-deployment/). Actions checkout submodules: [GitHub docs](https://github.com/actions/checkout#usage).

{{< callout type="warning" title="--delete" >}}
`rsync --delete` removes files on the server that are not in `public/`. Correct for static sites; terrifying if `DEPLOY_PATH` is wrong. Dry-run first: `rsync -avzn public/ user@host:/path/`.
{{< /callout >}}

---

## Step 4 — hugo.toml baseURL

```toml
baseURL = "https://yourdomain.dev/"
```

Wrong `baseURL` breaks CSS paths and sitemap URLs. Hugo discourse on Nginx 403s: [discourse.gohugo.io/t/help-deploying-with-nginx/12609](https://discourse.gohugo.io/t/help-deploying-with-nginx/12609).

---

## Step 5 — Local dry run

```bash
git submodule update --init --recursive
hugo --minify
ls public/index.html
python3 -m http.server -d public 8080
```

---

## Verification

1. Push a trivial commit to `main`
2. Actions tab → green workflow
3. `curl -sI https://yourdomain.dev/ | head -3`
4. View source — check `google-site-verification` if secret set

---

## Rollback

Keep last good build:

```bash
# on VPS before deploy (optional cron)
tar -czf ~/public-backup-$(date +%F).tar.gz -C /var/www/yoursite public
```

Restore: extract tarball into `/var/www/yoursite/`.

---

## Troubleshooting

**Submodule empty on CI** — `submodules: recursive` required for PaperMod.

**Permission denied (publickey)** — `DEPLOY_KEY` must match authorized_keys; user must own `DEPLOY_PATH`.

**Site looks unstyled** — `baseURL` mismatch or Cloudflare caching old CSS — purge cache in dashboard.

---

## Next steps

1. [Cloudflare edge setup](/infrastructure/cloudflare-nginx-vps-static-site-api/)
2. [Newsletter API on same VPS](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/)
3. [Full build log with Cursor prompts](/build-technical-blog-cursor-hugo/)
4. [Start Here learning path](/start-here/)

---

*Affiliate links may appear in partner boxes. [Affiliate Disclosure](/affiliate-disclosure/).*
