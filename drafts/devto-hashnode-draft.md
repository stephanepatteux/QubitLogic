---
# DEV.to front matter — paste this block when creating a new post on dev.to
title: How to Build a Technical Blog with Cursor and Hugo (2026)
published: true
description: Build a fast technical blog with Cursor and Hugo — SVG logo, self-hosted newsletter, GDPR compliance, Nginx security. Full working stack for under £10/month.
tags: cursor, hugo, webdev, devops
canonical_url: https://qubitlogic.dev/build-technical-blog-cursor-hugo/
cover_image: https://qubitlogic.dev/images/og-build-cursor-hugo.png
---

# HASHNODE FRONT MATTER (use instead of above on Hashnode):
# title: "How to Build a Technical Blog with Cursor and Hugo (2026)"
# tags: [cursor, hugo, webdev, devops]
# canonical: https://qubitlogic.dev/build-technical-blog-cursor-hugo/
# coverImage: https://qubitlogic.dev/images/og-build-cursor-hugo.png

---

> **Originally published at [qubitlogic.dev](https://qubitlogic.dev/build-technical-blog-cursor-hugo/)**

QubitLogic launched with 20+ articles, a working newsletter, a self-hosted subscription API, and an automated deploy pipeline — all running for under £10/month. This is the full build log, including the bits most tutorials skip: the logo, legal compliance, and security hardening.

**Cursor** was the coding environment for every file in this project. I'll include the actual prompts used at each step so you can replicate the workflow, not just the code.

| | |
|:---|:---|
| **Monthly cost** | ~$6–8/mo (VPS only) |
| **Annual cost** | ~£10 domain + ~$84 VPS |
| **Hugo build time** | < 6 seconds for 223 pages |
| **GitHub Actions deploy** | ~2 min 30 sec push-to-live |
| **Stack runtime dependencies** | 0 (static HTML + 1 FastAPI service) |
| **Time to build** | 1–2 weekends |
| **Cursor free tier sufficient?** | Yes |

---

## The Full Stack at a Glance

| Layer | Tool | Cost |
|:---|:---|:---|
| Editor | [Cursor](https://cursor.com) | Free tier / paid plans |
| Static site generator | [Hugo](https://gohugo.io/) | Free |
| Theme | [PaperMod](https://github.com/adityatelange/hugo-PaperMod) | Free |
| Logo | Cursor + hand-coded SVG | Free |
| Source control | [GitHub](https://github.com/) | Free |
| CI/CD | [GitHub Actions](https://github.com/features/actions) | Free (2,000 min/mo) |
| VPS hosting | DigitalOcean or Vultr | ~$6–12/mo |
| Web server | [Nginx](https://nginx.org/) | Free |
| OS | Ubuntu 24.04 LTS | Free |
| Domain registrar | Namecheap | ~£10/yr |
| DNS / CDN | [Cloudflare](https://cloudflare.com/) | Free |
| Newsletter API | [FastAPI](https://fastapi.tiangolo.com/) + SQLite | Free |
| Transactional email | Zoho Mail | Free tier |
| SSL | Let's Encrypt + Certbot | Free |

**Total recurring cost: ~$8/month VPS + ~£10/year domain.**

---

## Why Hugo? (And Why Not Astro, Ghost, or WordPress)

If you have looked at static site generators recently, you have seen the argument that **Astro is winning the AI-assisted development space** in 2026 because LLMs have more training data on JSX than on Go templates. That is a fair point for certain teams. Here is why Hugo was still the right call for this project — and when it might not be for yours.

| Criterion | Hugo | Astro | Ghost | WordPress |
|:---|:---|:---|:---|:---|
| Build speed | ✅ <1 s for 50 pages | ⚠️ 5–20× slower | ⚠️ Runtime (Node) | ❌ PHP runtime |
| AI-assisted editing (Cursor) | ✅ Works well | ✅ Better JS tooling | ⚠️ Less codeable | ⚠️ PHP complexity |
| Hosting requirement | ✅ Static HTML | ✅ Static HTML | ❌ Node + MySQL | ❌ PHP + MySQL |
| Built-in newsletter | ❌ Add FastAPI | ❌ External service | ✅ Built-in | ⚠️ Plugin |
| Maintenance overhead | ✅ None at runtime | ✅ Low | ⚠️ Node updates | ❌ High |
| Cost | ✅ Free | ✅ Free | ✅ Free (self-host) | ✅ Free (self-host) |

**Choose Hugo when:** you want zero runtime, your content is Markdown, and you are comfortable with Git workflows.

**Choose Astro instead when:** your team is JS/TS-first and you want React or Svelte components mixed into pages.

**QubitLogic is Hugo because:** fast builds, zero server runtime, and the infrastructure cost is just the VPS.

---

## Step 1 — Install Cursor

Before anything else, get your editor. I used [Cursor](https://cursor.com) for every file in this project — Hugo templates, GitHub Actions YAML, CSS, FastAPI backend, and every line of custom config.

Cursor is a VS Code fork with built-in AI: inline edits, an agent that reads your whole codebase, and a chat panel you describe problems to. The free tier is enough to bootstrap a site like this.

---

## Step 2 — Register a Domain (Namecheap + Cloudflare)

Pick a short `.dev` or `.io` domain. I used **Namecheap** for `qubitlogic.dev` — WHOIS privacy is included at no extra cost, renewal pricing is predictable, and the dashboard is straightforward.

Once registered, immediately point your nameservers to **Cloudflare**:

1. Sign up at [cloudflare.com](https://cloudflare.com/) (free)
2. Add your site → Cloudflare gives you two nameservers
3. Replace the nameservers in Namecheap's dashboard with the Cloudflare ones
4. Propagation takes 10–30 minutes

Cloudflare gives you free DNS, DDoS mitigation, SSL edge termination, and keeps your VPS IP hidden from the public internet.

> **Cursor prompt used:**
> *"Write me an nginx.conf snippet that plays well with Cloudflare full-strict SSL — no redirect loops, correct X-Forwarded-For headers."*

---

## Step 3 — Provision a VPS

**Why a VPS instead of GitHub Pages or Cloudflare Pages?**

Every competing tutorial in this space uses free static hosting. Here is why this stack uses a paid VPS instead:

| Factor | GitHub Pages / Cloudflare Pages | VPS ($6/mo) |
|:---|:---|:---|
| Hosting cost | Free | ~$6/mo |
| Self-hosted newsletter API | ❌ No server-side code | ✅ Run FastAPI + SQLite |
| GDPR data control | ❌ Data on US platform | ✅ You own the server |
| Custom Nginx config | ❌ Not possible | ✅ Full control |
| Ability to run cron jobs / agents | ❌ | ✅ |

If you only want a static blog with no newsletter and no server-side code, GitHub Pages is free and fine. The moment you add a newsletter, a $6/mo VPS pays for itself from the first affiliate conversion.

Choose **Ubuntu 24.04 LTS** when creating the instance. Use SSH key authentication, not a password.

```bash
# Once provisioned, create a non-root deploy user
adduser deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy

# Harden SSH — no root login, no password auth
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

> **Cursor prompt used:**
> *"Write a bash one-liner that disables root SSH login and password authentication in /etc/ssh/sshd_config without breaking the file, then restarts sshd."*

---

## Step 4 — Install Hugo Locally

Hugo is a Go static site generator. No Node.js, no build pipeline, no `node_modules` folder.

```bash
# macOS
brew install hugo

# Windows
winget install Hugo.Hugo.Extended

# Ubuntu/Debian
sudo snap install hugo
```

---

## Step 5 — Create the Site and Install PaperMod

```bash
hugo new site qubitlogic
cd qubitlogic
git init
git submodule add --depth=1 https://github.com/adityatelange/hugo-PaperMod themes/PaperMod
```

Edit `hugo.toml`:

```toml
baseURL = "https://yourdomain.dev/"
title = "Your Site"
theme = "PaperMod"
enableRobotsTXT = true

[params]
  defaultTheme = "dark"
  ShowReadingTime = true
  ShowToc = true
  ShowCodeCopyButtons = true
  ShowBreadCrumbs = true
```

PaperMod ships with dark mode, TOC, search, code copy buttons, and series navigation. None of that needs building from scratch.

---

## Step 6 — Design the Logo with Cursor

The logo is an atomic/quantum orbital motif: two crossing ellipses representing electron orbits, a green nucleus dot in the centre, and two green qubit nodes on the orbital paths.

> **Cursor prompt used:**
> *"Write an SVG logo for a quantum computing blog. It should show two crossing ellipses at different angles — like electron orbitals — with a central circle as the nucleus and two smaller circles at different points on the orbits. Use #00e87a (bright green) for the circles and currentColor for the ellipses so it adapts to dark/light mode. ViewBox 64x64, no external dependencies."*

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none">
  <ellipse cx="32" cy="32" rx="28" ry="10" stroke="currentColor"
           stroke-width="2.5" transform="rotate(-30 32 32)"/>
  <ellipse cx="32" cy="32" rx="28" ry="10" stroke="currentColor"
           stroke-width="2.5" transform="rotate(30 32 32)"/>
  <circle cx="32" cy="32" r="4.5" fill="#00e87a"/>
  <circle cx="11" cy="27" r="3" fill="#00e87a"/>
  <circle cx="53" cy="37" r="3" fill="#00e87a"/>
</svg>
```

Because the ellipses use `currentColor`, they automatically switch between dark and light mode.

---

## Step 7 — Write Content in Markdown

Every article is a `.md` file under `content/`. Hugo reads **front matter** (YAML at the top) for metadata:

```markdown
---
title: "My Article Title"
date: 2026-06-01T08:30:00+01:00
tags: ["vps", "ubuntu"]
categories: ["tutorial"]
description: "Under 155 chars, keyword first..."
---

Your content starts here...
```

> **Cursor prompt used:**
> *"I'm writing a Hugo article about X. Generate a front matter block with a good SEO description under 160 characters, 5–7 relevant tags, and a summary under 50 words."*

---

## Step 8 — Custom CSS Without Fighting the Theme

Hugo loads CSS from `assets/css/extended/`. Any `.css` file there is included automatically.

```css
:root {
  --qs-green: #00e87a;
  --qs-font-mono: "JetBrains Mono", monospace;
  --qs-radius: 10px;
}
```

> **Cursor prompt used:**
> *"Write CSS for a recommendation box component: a card with a badge pill positioned top-left, name in bold, a short description in muted colour, and a green CTA button right-aligned. Should work in both dark and light mode using CSS custom properties."*

---

## Step 9 — Hugo Shortcodes for Reusable Components

Shortcodes are Hugo's component system. Templates live in `layouts/shortcodes/`:

```html
{{/* layouts/shortcodes/callout.html */}}
{{ $type  := .Get "type"  | default "info" }}
{{ $title := .Get "title" | default "" }}

<div class="qs-callout qs-callout--{{ $type }}" role="note">
  {{ if $title }}<p class="qs-callout-title">{{ $title }}</p>{{ end }}
  <div class="qs-callout-body">{{ .Inner | markdownify }}</div>
</div>
```

> **Cursor prompt used:**
> *"Write a Hugo shortcode called affiliate_box. Parameters: name, url, cta, badge, desc, price, offer. The URL should resolve from a lookup table: if url equals 'AFFILIATE_LINK_DIGITALOCEAN', use site.Params.affiliates.digitalocean. Render a card with the badge, content, and a CTA button."*

---

## Step 10 — GitHub Actions Automated Deployment

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true
          fetch-depth: 0

      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: latest
          extended: true

      - name: Build
        run: hugo --minify

      - name: Deploy via rsync
        uses: burnett01/rsync-deployments@7.0.1
        with:
          switches: -avz --delete
          path: public/
          remote_path: /var/www/yourdomain/
          remote_host: ${{ secrets.VPS_HOST }}
          remote_user: deploy
          remote_key: ${{ secrets.VPS_SSH_KEY }}
```

Every `git push` to `main` builds and deploys automatically. From Cursor's terminal: write, commit, push, live in under 2 minutes.

---

## Step 11 — HTTPS with Let's Encrypt

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.dev -d www.yourdomain.dev
```

Set Cloudflare SSL/TLS mode to **Full (strict)** to prevent redirect loops.

---

## Step 12 — Security Hardening (Nginx Headers)

> **Cursor prompt used:**
> *"Write Nginx add_header directives for a static site with no inline scripts or styles. Include: Content-Security-Policy (strict, no unsafe-inline), X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy. Explain each header in a comment."*

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none';" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

Test at [securityheaders.com](https://securityheaders.com/) — aim for A or A+.

---

## Step 13 — Compliance: Privacy, Cookies, and Affiliate Disclosure

| Requirement | Why | What to do |
|:---|:---|:---|
| **Privacy Policy** | UK GDPR, EU GDPR | Required if you collect any data |
| **Cookie notice** | ePrivacy Directive | Required if you use analytics cookies |
| **Affiliate disclosure** | ASA CAP Code (UK), FTC (US) | Required on any page with commission-earning links |
| **Newsletter double opt-in** | GDPR consent mechanism | Required — single opt-in is insufficient |

A pure Hugo static site with no analytics scripts does **not** need a cookie banner. Hugo doesn't set cookies. PaperMod doesn't set cookies. Nginx doesn't set cookies. You only need a banner if you add Google Analytics.

> **Cursor prompt used:**
> *"Write a GDPR-compliant privacy policy for a UK-based technical blog. Data collected: email addresses for a newsletter (double opt-in, SQLite on a UK VPS, deleted on unsubscribe), standard Nginx access logs (IP anonymised after 24 hours)."*

---

## Step 14 — Self-Hosted Newsletter (FastAPI + SQLite)

No Mailchimp. No Beehiiv. A FastAPI app on the same VPS, backed by SQLite.

```python
import os, sqlite3, secrets, smtplib, ssl
from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import HTMLResponse
from email.message import EmailMessage

app = FastAPI()
DB   = os.getenv("NEWSLETTER_DB", "/var/lib/yoursite/newsletter.db")
SITE = os.getenv("SITE_URL", "https://yourdomain.dev")

def get_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        email TEXT PRIMARY KEY,
        token TEXT UNIQUE NOT NULL,
        confirmed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    return con

@app.post("/api/newsletter/subscribe")
async def subscribe(email: str = Form(...)):
    token = secrets.token_urlsafe(32)
    db = get_db()
    try:
        db.execute("INSERT INTO subscribers (email, token) VALUES (?, ?)", (email, token))
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Already subscribed or pending confirmation.")
    send_confirmation(email, token)
    return HTMLResponse("<p>Check your email to confirm your subscription.</p>")

@app.get("/api/newsletter/confirm")
async def confirm(token: str = Query(...)):
    db = get_db()
    row = db.execute(
        "UPDATE subscribers SET confirmed=1 WHERE token=? AND confirmed=0", (token,)
    ).rowcount
    db.commit()
    if not row:
        raise HTTPException(400, "Invalid or already confirmed token.")
    return HTMLResponse("<p>Subscribed! You'll receive the next issue.</p>")

@app.get("/api/newsletter/unsubscribe")
async def unsubscribe(token: str = Query(...)):
    db = get_db()
    db.execute("DELETE FROM subscribers WHERE token=?", (token,))
    db.commit()
    return HTMLResponse("<p>Unsubscribed. Your data has been deleted.</p>")
```

Transactional email via **Zoho Mail free tier** — up to 5 addresses with SMTP. More than enough for newsletter confirmations.

---

## The `.cursorrules` File for Hugo

Drop this in your repository root as `.cursorrules` — it eliminates the most common Cursor hallucinations for Hugo projects:

```
# Cursor rules for Hugo + PaperMod

## Project context
- Hugo v0.162+ (extended), theme: PaperMod (themes/PaperMod/)
- All content in content/ as Markdown with YAML front matter
- Custom layouts in layouts/ override PaperMod defaults
- Custom shortcodes in layouts/shortcodes/
- Custom CSS in assets/css/extended/ (auto-merged by PaperMod)

## Hugo templating rules
- Variable scoping: use `{{ $var := . }}` at the top of {{ with }} / {{ range }} blocks
- Accessing site params inside range: use {{ site.Params.foo }} not {{ .Site.Params.foo }}
- Front matter: YAML only. Required: title, date, draft, description, tags, categories
- Date format: 2026-06-04T18:00:00+01:00 — always include timezone offset

## Do not
- Do not edit anything in themes/ — override in layouts/ instead
- Do not use {{ .Site.Params }} — use {{ site.Params }} (Hugo v0.113+ syntax)
```

---

## Frequently Asked Questions

**Why Hugo over WordPress?**
Hugo generates static HTML — no attack surface at runtime, no CMS to patch, pages load faster. For a developer writing in Markdown with Git, Hugo fits the workflow.

**Is Hugo harder than Astro for AI-assisted development?**
In practice, no. Cursor handles Hugo templates well when you give it context. The limiting factor is writing clear prompts, not the framework. Hugo wins on operational simplicity: one Go binary, no Node toolchain, sub-second builds.

**How much does this stack cost per month?**
About **$6–8/month** (VPS) plus roughly **£10/year** for the domain. Everything else is free.

**Do I need to know Go to use Hugo?**
No. Hugo's templating language is a simplified subset. Cursor drafts the syntax from plain English descriptions.

**How long does the whole build take?**
One to two weekends for the full stack. Writing the first batch of articles takes longer than building the infrastructure.

---

*Full article with shortcode examples, affiliate boxes, and additional detail: [qubitlogic.dev/build-technical-blog-cursor-hugo/](https://qubitlogic.dev/build-technical-blog-cursor-hugo/)*
