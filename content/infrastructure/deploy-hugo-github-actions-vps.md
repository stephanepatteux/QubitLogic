---
title: "Deploy Hugo to VPS: GitHub Actions & rsync"
date: 2026-06-06T14:00:00+01:00
lastmod: 2026-06-06T16:00:00+01:00
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
  - q: "Why pin the Hugo version in GitHub Actions?"
    a: "Hugo minor releases occasionally change behaviour (pagination, Goldmark, module resolution). Pinning hugo-version to match your local install prevents CI building differently than your laptop. QubitLogic pins 0.162.1 — update deliberately after testing locally."
  - q: "How do I fix Host key verification failed in the rsync step?"
    a: "Add an ssh-keyscan step before rsync to populate known_hosts for your VPS IP. GitHub runners start with an empty known_hosts file. See the workflow fix in Step 3 below."
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

The VPS does **not** need Hugo, Go, or Node installed. Production only serves pre-built HTML from `public/`. That separation is the main reason CI + rsync beats `git pull && hugo` on the server: your production box never drifts because a package update broke the build toolchain.

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

Generate a deploy-only key pair on your laptop (do not reuse your personal SSH key):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_ed25519 -N ""
cat ~/.ssh/deploy_ed25519.pub   # → append to ~/.ssh/authorized_keys on VPS
cat ~/.ssh/deploy_ed25519       # → paste entire block into DEPLOY_KEY secret
```

Restrict the key to rsync if you want defence in depth — for most solo blogs, a dedicated key with no passphrase is sufficient.

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

      - name: Add VPS to known_hosts
        run: ssh-keyscan -H "${{ secrets.DEPLOY_HOST }}" >> ~/.ssh/known_hosts

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

The `ssh-keyscan` step fixes the most common first-time failure: **Host key verification failed**. GitHub runners start with an empty `known_hosts` file on every run.

Hugo hosting docs: [gohugo.io/hosting-and-deployment](https://gohugo.io/hosting-and-deployment/). Actions checkout submodules: [GitHub docs](https://github.com/actions/checkout#usage).

### Why pin `hugo-version`?

`latest` in CI is a trap. Hugo 0.140 and 0.162 can produce different HTML from the same source — pagination changes, Goldmark defaults, module resolution. Pin the version to match your local machine:

```bash
hugo version   # locally — use this string in the workflow
```

When you upgrade, test `hugo --minify` locally first, then bump the workflow pin in the same commit.

### What `fetch-depth: 0` does

Hugo's `.GitInfo` and `.Lastmod` need full Git history. Shallow clones (`fetch-depth: 1`, the default) leave `lastmod` empty on article pages. `fetch-depth: 0` fetches all commits — slightly slower checkout, correct dates in sitemaps and Open Graph.

{{< callout type="warning" title="--delete" >}}
`rsync --delete` removes files on the server that are not in `public/`. Correct for static sites; terrifying if `DEPLOY_PATH` is wrong. Dry-run first: `rsync -avzn public/ user@host:/path/`.
{{< /callout >}}

---

## Step 4 — hugo.toml baseURL

```toml
baseURL = "https://yourdomain.dev/"
```

Wrong `baseURL` breaks CSS paths and sitemap URLs. Hugo discourse on Nginx 403s: [discourse.gohugo.io/t/help-deploying-with-nginx/12609](https://discourse.gohugo.io/t/help-deploying-with-nginx/12609).

Common `baseURL` mistakes:

| `baseURL` value | Symptom |
|-----------------|---------|
| `http://localhost:1313/` | CSS 404 in production; canonical URLs point at localhost |
| `https://example.com` (no trailing slash) | Relative URLs break on nested pages |
| `https://www.example.com/` but Nginx serves bare domain | Mixed-content or redirect loops with Cloudflare |

Rule: **match exactly what users type in the browser**, including `https://` and trailing `/`.

### Optional: Search Console verification at build time

Two options — pick one:

1. **GitHub secret** — set `GOOGLE_SITE_VERIFICATION` in Actions secrets; pass it as a build env var (already shown in the workflow above). Your head partial reads `getenv "GOOGLE_SITE_VERIFICATION"`.
2. **`hugo.toml`** — paste the tag content directly:

```toml
[params.analytics.google]
  SiteVerificationTag = "your-verification-string-from-search-console"
```

The meta tag is baked into HTML at build time — no runtime PHP or JavaScript required. QubitLogic uses the env-var approach so the verification string never sits in the public repo.

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

## Common mistakes

1. **`submodules: true` instead of `recursive`** — PaperMod installs as an empty directory; site builds with no CSS. Use `submodules: recursive`.

2. **Wrong `DEPLOY_PATH`** — `rsync --delete` to `/var/www/` instead of `/var/www/yoursite/public/` deletes unrelated files. Always dry-run: `rsync -avzn public/ deploy@host:/path/`.

3. **Hugo not Extended** — SCSS pipelines (PaperMod, custom CSS) fail silently or skip minification. Set `extended: true` in `peaceiris/actions-hugo`.

4. **Building with `draft: true` posts** — fine locally, but remember `hugo --minify` in CI respects draft flags unless you pass `-D`. Production workflows should not use `-D`.

5. **Forgetting trailing slash on `DEPLOY_PATH`** — rsync creates a nested `public/public/` directory. Use `/var/www/yoursite/public/` with trailing slash.

6. **Deploy key has a passphrase** — GitHub Actions cannot prompt. Generate with `-N ""` or use `ssh-agent` in a custom step.

7. **Cloudflare caches a broken deploy** — after fixing `baseURL`, purge cache in Cloudflare → Caching → Purge Everything.

---

## Troubleshooting

**Submodule empty on CI** — `submodules: recursive` required for PaperMod. Locally run `git submodule update --init --recursive` and commit the submodule pointer.

**Permission denied (publickey)** — `DEPLOY_KEY` must be the **private** key matching an entry in `~deploy/.ssh/authorized_keys`. Check file permissions: `chmod 600 authorized_keys`.

**Host key verification failed** — add the `ssh-keyscan` step shown in Step 3.

**Site looks unstyled** — three causes in order: (1) `baseURL` mismatch — view source and check CSS `href` paths; (2) theme submodule empty in CI; (3) Cloudflare serving stale CSS — purge cache.

**404 on article pages but homepage works** — Nginx `try_files` missing `$uri $uri/` fallback. Hugo generates `post/index.html` for clean URLs:

```nginx
location / {
    try_files $uri $uri/ =404;
}
```

**Actions pass but site unchanged** — wrong branch trigger (`on.push.branches`), or `DEPLOY_PATH` points at a directory Nginx does not serve. SSH in and `ls -la /var/www/yoursite/public/`.

**Hugo build fails on SCSS** — need Extended edition. Error mentions `toCSS` or `resources.ExecuteAsTemplate` — set `extended: true`.

---

## Frequently Asked Questions

### Why rsync instead of git pull on the VPS?

The VPS only needs static HTML — not your Git history, Hugo binary, or theme source. rsync pushes the built `public/` folder in seconds and avoids installing Hugo on production. `git pull` on the server couples deploy to server tooling and makes rollbacks harder.

### Why do I need `submodules: recursive` in GitHub Actions?

PaperMod and most Hugo themes are Git submodules. Without recursive checkout, CI builds with an empty `themes/` folder — you get an unstyled site.

### Is rsync `--delete` safe for Hugo deploys?

Yes, when `DEPLOY_PATH` points at your Nginx docroot (e.g. `/var/www/yoursite/public/`). `--delete` removes stale files from old builds. Dry-run first with `rsync -avzn` if you are nervous.

### Why pin the Hugo version in GitHub Actions?

Hugo minor releases occasionally change behaviour. Pinning `hugo-version` to match your local install prevents CI building differently than your laptop.

### How do I fix Host key verification failed in the rsync step?

Add `ssh-keyscan -H "${{ secrets.DEPLOY_HOST }}" >> ~/.ssh/known_hosts` before the rsync step. GitHub runners start with an empty known_hosts file.

---

## Next steps

1. [Cloudflare edge setup](/infrastructure/cloudflare-nginx-vps-static-site-api/)
2. [Newsletter API on same VPS](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/)
3. [Full build log with Cursor prompts](/build-technical-blog-cursor-hugo/)
4. [Start Here learning path](/start-here/)

---

*Affiliate links may appear in partner boxes. [Affiliate Disclosure](/affiliate-disclosure/).*
