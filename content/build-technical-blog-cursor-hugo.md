---
title: "Build a Hugo Blog with Cursor AI: Full 2026 Setup Guide"
seoTitle: "Build a Hugo Blog with Cursor AI (2026)"
date: 2026-06-04T18:00:00+01:00
lastmod: 2026-06-28T12:00:00+01:00
draft: false
description: "Build a Hugo blog with Cursor AI — PaperMod theme, GitHub Actions deploy, self-hosted newsletter API, and Nginx hardening. Full QubitLogic build log with real prompts."
summary: "The complete walkthrough of how QubitLogic was built: Hugo static site, PaperMod theme, SVG logo from scratch, GitHub Actions CI/CD, self-hosted FastAPI newsletter, UK GDPR compliance, Nginx security headers — all with real Cursor prompts used along the way. Most of the stack is free."
keywords: ["build a blog with cursor", "hugo blog tutorial 2026", "hugo papermod tutorial", "self-hosted newsletter python", "cursor ai blog setup", "github actions hugo deploy", "hugo vs astro 2026", "technical blog free stack vps"]
tags: ["cursor", "hugo", "vps", "python", "github-actions", "build-in-public", "devops", "newsletter", "security", "compliance"]
categories: ["build"]
images: ["/images/og-build-cursor-hugo.png"]
weight: 99
ShowToc: true
TocOpen: true
ShowReadingTime: true
schema_howto: true
---

QubitLogic launched with 20+ articles, a working newsletter, a self-hosted subscription API, and an automated deploy pipeline — all running for under £10/month. This is the full build log, including the bits most tutorials skip: the logo, legal compliance, and security hardening.

**Cursor** was the coding environment for every file in this project. I'll include the actual prompts used at each step so you can replicate the workflow, not just the code.

Most of the stack is free. Hosting is the only recurring cost.

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
| Editor | [Cursor](https://cursor.com/referral?code=TKHKBWB8304Q) | Free tier / paid plans |
| Static site generator | [Hugo](https://gohugo.io/) | Free |
| Theme | [PaperMod](https://github.com/adityatelange/hugo-PaperMod) | Free |
| Logo | Cursor + hand-coded SVG | Free |
| Source control | [GitHub](https://github.com/) | Free |
| CI/CD | [GitHub Actions](https://github.com/features/actions) | Free (2,000 min/mo) |
| VPS hosting | {{< affiliate_link url="AFFILIATE_LINK_DIGITALOCEAN" >}}DigitalOcean{{< /affiliate_link >}} or [Vultr](https://www.vultr.com/?ref=9904429-9J) | ~$6–12/mo |
| Web server | [Nginx](https://nginx.org/) | Free |
| OS | Ubuntu 24.04 LTS | Free |
| Domain registrar | [Dynadot](https://www.dynadot.com/) | ~£10/yr |
| DNS / CDN | [Cloudflare](https://cloudflare.com/) | Free |
| Newsletter API | [FastAPI](https://fastapi.tiangolo.com/) + [SQLite](https://sqlite.org/) | Free |
| Transactional email | [Zoho Mail](https://www.zoho.com/mail/) | Free tier |
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

**Choose Hugo when:**
- You want zero runtime — no Node process to crash, no database to back up, no security patches for the CMS
- Your content is Markdown and you want build times under one second regardless of article count
- You are comfortable with Git-based workflows

**Choose Astro instead when:**
- Your team is primarily JavaScript/TypeScript and you want React or Svelte components mixed into pages
- You are building a marketing site with interactive islands
- You want Cursor's AI to work with more familiar JSX syntax

**QubitLogic is Hugo because:** fast builds, zero server runtime, and the infrastructure cost is just the VPS. Cursor handled every Go template edit without issue — the AI friction is lower than the 2026 narrative suggests once you give it enough context about the Hugo data model.

---

## Step 1 — Install Cursor

Before anything else, get your editor. I used [Cursor](https://cursor.com/referral?code=TKHKBWB8304Q) for every file in this project — Hugo templates, GitHub Actions YAML, CSS, FastAPI backend, and every line of custom config.

Cursor is a VS Code fork with built-in AI: inline edits, an agent that reads your whole codebase, and a chat panel you describe problems to. The free tier is enough to bootstrap a site like this.

Install from [cursor.com](https://cursor.com/referral?code=TKHKBWB8304Q). It opens exactly like VS Code — same extensions, same keybindings, same integrated terminal.

{{< affiliate_box
    name="Cursor"
    url="AFFILIATE_LINK_CURSOR"
    cta="Try Cursor free"
    offer="Referral link · free tier to start"
    badge="AI-assisted IDE"
    primary="true"
    desc="The editor used to write every file in this project — Hugo templates, FastAPI newsletter backend, GitHub Actions workflows, custom CSS, and the SVG logo."
    price="Free tier; paid plans for heavy use"
>}}

---

## Step 2 — Register a Domain (Dynadot + Cloudflare)

Pick a short `.dev` or `.io` domain. **Dynadot** offers competitive renewals, WHOIS privacy on most TLDs, and an in-house **Ambassador** affiliate programme (30% on registrations) — often easier to join than large Impact networks when your site is still growing.

{{< affiliate_box
    name="Dynadot"
    url="AFFILIATE_LINK_DYNADOT"
    cta="Search domains"
    badge="Ambassador programme"
    desc="Register your domain, then point nameservers to Cloudflare. Apply at dynadot.com/affiliate for referral links."
    price=".dev from ~£10/yr"
>}}

Once registered, immediately point your nameservers to **Cloudflare**:

1. Sign up at [cloudflare.com](https://cloudflare.com/) (free)
2. Add your site → Cloudflare gives you two nameservers
3. Replace the nameservers in your registrar's dashboard (Dynadot → Domain → Nameservers) with the Cloudflare ones
4. Propagation takes 10–30 minutes

Cloudflare gives you free DNS, DDoS mitigation, SSL edge termination, and keeps your VPS IP hidden from the public internet. It costs nothing.

> **Cursor prompt used:**
> *"Write me an nginx.conf snippet that plays well with Cloudflare full-strict SSL — no redirect loops, correct X-Forwarded-For headers."*

---

## Step 3 — Provision a VPS

You need a server. I benchmarked {{< affiliate_link url="AFFILIATE_LINK_DIGITALOCEAN" >}}DigitalOcean{{< /affiliate_link >}} and [Vultr](https://www.vultr.com/?ref=9904429-9J) for a [separate article on this site](/infrastructure/digitalocean-vs-vultr-performance-benchmarks/). For a static Hugo site plus a lightweight newsletter API, the **$6/mo plan** (1 vCPU, 1 GB RAM) is plenty.

{{< affiliate_stack >}}

**Why a VPS instead of GitHub Pages or Cloudflare Pages?**

Every competing tutorial in this space uses free static hosting. Here is why this stack uses a paid VPS instead:

| Factor | GitHub Pages / Cloudflare Pages | VPS ($6/mo) |
|:---|:---|:---|
| Hosting cost | Free | ~$6/mo |
| Self-hosted newsletter API | ❌ No server-side code | ✅ Run FastAPI + SQLite |
| GDPR data control | ❌ Data on US platform | ✅ You own the server |
| Custom Nginx config | ❌ Not possible | ✅ Full control |
| Affiliate tracking flexibility | ❌ Limited | ✅ Any server-side redirect |
| Ability to run cron jobs / agents | ❌ | ✅ |
| SSL | ✅ Automatic | ✅ Let's Encrypt / Certbot |

**The summary:** if you only want a static blog with no newsletter and no server-side code, GitHub Pages is free and fine. The moment you add a newsletter, any server-side feature, or want full data sovereignty, a $6/mo VPS pays for itself from the first affiliate conversion.

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

Hugo is a Go static site generator. No Node.js, no build pipeline, no `node_modules` folder. It turns Markdown into a full site in under 5 seconds.

```bash
# macOS
brew install hugo

# Windows
winget install Hugo.Hugo.Extended

# Ubuntu/Debian
sudo snap install hugo
```

```bash
hugo version
# hugo v0.147.x+extended linux/amd64
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

```bash
hugo server -D
# open http://localhost:1313
```

PaperMod ships with dark mode, TOC, search, code copy buttons, and series navigation. None of that needs building from scratch.

---

## Step 6 — Design the Logo with Cursor

This is where most tutorials say "use Canva" or "hire someone." I built the QubitLogic logo directly in SVG with Cursor — it took about 20 minutes.

The logo is an atomic/quantum orbital motif: two crossing ellipses representing electron orbits, a green nucleus dot in the centre, and two green qubit nodes on the orbital paths.

> **Cursor prompt used:**
> *"Write an SVG logo for a quantum computing blog. It should show two crossing ellipses at different angles — like electron orbitals — with a central circle as the nucleus and two smaller circles at different points on the orbits. Use #00e87a (bright green) for the circles and currentColor for the ellipses so it adapts to dark/light mode. ViewBox 64x64, no external dependencies."*

The result, after minor tweaks:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none">
  <!-- Orbit 1: angled one way -->
  <ellipse cx="32" cy="32" rx="28" ry="10" stroke="currentColor"
           stroke-width="2.5" transform="rotate(-30 32 32)"/>
  <!-- Orbit 2: angled the other way -->
  <ellipse cx="32" cy="32" rx="28" ry="10" stroke="currentColor"
           stroke-width="2.5" transform="rotate(30 32 32)"/>
  <!-- Nucleus -->
  <circle cx="32" cy="32" r="4.5" fill="#00e87a"/>
  <!-- Qubit nodes on orbits -->
  <circle cx="11" cy="27" r="3" fill="#00e87a"/>
  <circle cx="53" cy="37" r="3" fill="#00e87a"/>
</svg>
```

Save as `static/images/logo-mark.svg`. Reference it in `hugo.toml`:

```toml
[params.label]
  icon = "/images/logo-mark.svg"
  iconHeight = 28
```

Because the ellipses use `currentColor` (not a hardcoded hex), they automatically switch between dark and light mode.

### Favicon

Generate a favicon from the same SVG. The easiest zero-install way:

1. Open your SVG in a browser
2. Screenshot it at 512×512
3. Upload to [favicon.io/favicon-converter](https://favicon.io/favicon-converter/) — it generates the full `favicon.ico`, `apple-touch-icon.png`, and `site.webmanifest`
4. Drop the output into `static/`

> **Cursor prompt used:**
> *"Write the <head> snippet for Hugo to include a favicon, apple-touch-icon, and web manifest. The files are at /favicon.ico, /apple-touch-icon.png, and /site.webmanifest."*

---

## Step 7 — Write Content in Markdown

Every article is a `.md` file under `content/`. Hugo reads **front matter** (YAML at the top) for metadata:

```markdown
---
title: "How to Provision a VPS for AI Agent Workloads"
date: 2026-06-01T08:30:00+01:00
tags: ["vps", "ubuntu", "ai-agents"]
categories: ["tutorial"]
description: "Step-by-step VPS setup for Python AI workloads..."
---

Your content starts here...
```

I wrote every QubitLogic article in Cursor. The workflow: open content folder, create a `.md` file, write in Markdown, preview with `hugo server`, commit. No CMS dashboard, no browser editor.

> **Cursor prompt used (typical):**
> *"I'm writing a Hugo article about X. Generate a front matter block with a good SEO description under 160 characters, 5–7 relevant tags, and a summary under 50 words."*

---

## Step 8 — Custom CSS Without Fighting the Theme

Hugo loads CSS from `assets/css/extended/`. Any `.css` file there is included automatically — no build step needed.

Create `assets/css/extended/custom.css`:

```css
:root {
  --qs-green: #00e87a;
  --qs-font-mono: "JetBrains Mono", monospace;
  --qs-radius: 10px;
}

/* Example: custom callout box */
.callout {
  border-left: 3px solid var(--qs-green);
  padding: 0.9rem 1.25rem;
  background: var(--entry);
  border-radius: 0 var(--qs-radius) var(--qs-radius) 0;
  margin: 1.75rem 0;
}
```

> **Cursor prompts used for CSS:**
> *"Write CSS for a recommendation box component: a card with a badge pill positioned top-left, name in bold, a short description in muted colour, and a green CTA button right-aligned. Should work in both dark and light mode using CSS custom properties."*
>
> *"Add a :hover state to .affiliate-btn that raises it slightly and darkens the background. Keep it subtle — max transform translateY(-1px)."*

Cursor is particularly useful for CSS because you describe the component visually rather than remembering property names.

---

## Step 9 — Hugo Shortcodes for Reusable Components

Shortcodes are Hugo's component system. Instead of copying raw HTML into every article, you write:

```markdown
{{</* callout type="tip" title="Pro tip" */>}}
Use Hugo's built-in minification — set `minifyOutput = true` in hugo.toml.
{{</* /callout */>}}
```

Shortcode templates live in `layouts/shortcodes/`:

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
> *"Write a Hugo shortcode called affiliate_box. Parameters: name, url, cta (default 'Get Started'), badge (optional pill label), desc, price, offer (optional green text shown above the name). The URL should resolve from a lookup table: if url equals 'AFFILIATE_LINK_DIGITALOCEAN', use site.Params.affiliates.digitalocean. Render a card with the badge, content, and a styled CTA button."*

I built a dozen shortcodes this way: affiliate boxes, callouts, benchmark tables, newsletter signup, partner boxes (for editorial-only links). Each one described to Cursor in plain English, first draft generated, then refined.

---

## Step 10 — Set Up GitHub and Automated Deployment

Push the site to GitHub, then automate deploy on every push to `main`.

```bash
git remote add origin https://github.com/yourusername/your-repo.git
git add .
git commit -m "initial site"
git push -u origin main
```

**Full deploy walkthrough:** the standalone guide [Deploy Hugo to VPS: GitHub Actions & rsync](/infrastructure/deploy-hugo-github-actions-vps/) covers the complete workflow — `peaceiris/actions-hugo`, submodule checkout, `rsync --delete`, GitHub secrets (`DEPLOY_HOST`, `DEPLOY_KEY`), and `baseURL` pitfalls. You do **not** need Hugo installed on the VPS; CI builds `public/` and rsyncs only static files.

On the server, create the Nginx docroot (`/var/www/yoursite/public`) and point `root` at it. For Cloudflare + Origin CA TLS, see [Cloudflare + Nginx on a VPS](/infrastructure/cloudflare-nginx-vps-static-site-api/).

Every `git push` to `main` builds and deploys automatically. From Cursor's terminal: write, commit, push, live in under 2 minutes.

> **Cursor prompt used:**
> *"My GitHub Actions deploy job is failing with 'Host key verification failed' on the rsync step. Write the fix — add a known_hosts setup step that accepts the VPS host key automatically without hardcoding it."*

---

## Step 11 — HTTPS with Let's Encrypt

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.dev -d www.yourdomain.dev
```

Follow the prompts, agree to TOS. Certbot modifies your Nginx config and sets up auto-renewal via a systemd timer. Done.

If routing through Cloudflare (recommended), set SSL/TLS mode to **Full (strict)** in the Cloudflare dashboard to prevent redirect loops.

---

## Step 12 — Security Hardening (Nginx Headers)

A static Hugo site has a small attack surface, but you still want proper HTTP security headers. This is purely configuration — no code — and Cursor drafts it faster than reading MDN.

> **Cursor prompt used:**
> *"Write Nginx add_header directives for a static site with no inline scripts or styles. Include: Content-Security-Policy (strict, no unsafe-inline), X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy (disable camera, microphone, geolocation). Explain each header in a comment."*

Add to your Nginx server block:

```nginx
# Prevent clickjacking
add_header X-Frame-Options "SAMEORIGIN" always;

# Stop MIME sniffing
add_header X-Content-Type-Options "nosniff" always;

# Don't send referrer on cross-origin requests
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Disable unused browser features
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

# Content Security Policy — adjust if you add third-party scripts
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none';" always;

# Tell browsers to use HTTPS for 1 year
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

Test your headers at [securityheaders.com](https://securityheaders.com/) — aim for A or A+.

Also harden the VPS itself:

```bash
# Firewall: only allow SSH, HTTP, HTTPS
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable

# Automatic security updates
apt install -y unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades
```

---

## Step 13 — Compliance: Privacy, Cookies, and Affiliate Disclosure

This is the section most "how to blog" tutorials ignore entirely. If you are in the UK or EU, or targeting those audiences, compliance is not optional.

### What you legally need

| Requirement | Why | What to do |
|:---|:---|:---|
| **Privacy Policy** | UK GDPR, EU GDPR | Required if you collect any data (newsletter emails, server logs) |
| **Cookie notice** | ePrivacy Directive (PECR in UK) | Required if you use analytics cookies; not required for strictly necessary ones |
| **Affiliate disclosure** | ASA CAP Code (UK), FTC (US) | Required on any page with commission-earning links |
| **Newsletter double opt-in** | GDPR consent mechanism | Required — single opt-in is insufficient in most EU jurisdictions |

### Privacy Policy

Create `content/privacy.md`. Cover:

- What personal data you collect (email for newsletter, IP in Nginx logs)
- How long you keep it
- Who you share it with (Zoho for email transit, GitHub for code)
- User rights under UK GDPR (access, erasure, portability)
- How to request deletion (email address)

> **Cursor prompt used:**
> *"Write a GDPR-compliant privacy policy for a UK-based technical blog. Data collected: email addresses for a newsletter (double opt-in, SQLite on a UK VPS, deleted on unsubscribe), standard Nginx access logs (IP anonymised after 24 hours). Email sent via Zoho Mail. No analytics cookies, no third-party trackers. Include sections on user rights under UK GDPR and a contact email for data requests."*

### Affiliate Disclosure

Create `content/affiliate-disclosure.md`. List every programme you participate in, what you earn, and your editorial independence policy. This is required by the ASA CAP Code in the UK and FTC guidelines in the US.

Auto-insert a notice at the top of every post that uses affiliate links. In `layouts/single.html`:

```html
{{- if in .RawContent "affiliate_box" }}
{{- partial "affiliate/top_notice.html" . }}
{{- end }}
```

And `layouts/partials/affiliate/top_notice.html`:

```html
<div class="affiliate-top-notice" role="note">
  <p>Partner offers below — we may earn a commission at no extra cost to you.
     <a href="/affiliate-disclosure/">Affiliate Disclosure</a></p>
</div>
```

### Cookies

A pure Hugo static site with no analytics and no tracking scripts does **not** need a cookie banner. Hugo does not set cookies. PaperMod does not set cookies. Nginx does not set cookies.

You only need a banner if you add Google Analytics, Facebook Pixel, or similar. I deliberately left those off QubitLogic — server-side Nginx logs are sufficient for basic traffic insights and require no cookie consent.

If you add analytics later, add [Klaro](https://klaro.org/) (open source, MIT) or [CookieYes](https://www.cookieyes.com/) (free tier available).

### Newsletter double opt-in

The FastAPI newsletter API (built in Step 14) uses double opt-in by design:

1. User submits email → stored as `confirmed = 0`
2. Confirmation email sent with a unique token link
3. User clicks link → `confirmed = 1`, they are added to the active list

This is the correct GDPR consent flow. Single opt-in is not compliant in most EU jurisdictions.

> **Cursor prompt used:**
> *"Write a Python function that generates a GDPR-compliant double opt-in confirmation email. It should: use secrets.token_urlsafe(32) for the token, build a confirmation URL with the token as a query parameter, send via SMTP with a plain-text fallback, and include an unsubscribe link in the footer."*

---

## Step 14 — Self-Hosted Newsletter

No Mailchimp, no Beehiiv, no SaaS that charges per subscriber. QubitLogic runs a FastAPI app on the same VPS, backed by SQLite, with double opt-in and Zoho SMTP for confirmation emails.

**Full tutorial:** [Self-Hosted Newsletter API: FastAPI, SQLite, No Mailchimp](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/) — complete code for subscribe/confirm/unsubscribe routes, `.env` setup, Nginx `/api/` proxy, Hugo form wiring, and SPF/DKIM/DMARC for deliverability.

**Prerequisites:** complete [Deploy FastAPI on Ubuntu 24.04](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) first — the newsletter API runs on the same Gunicorn + systemd stack.

### Transactional email — Zoho Mail free tier

Zoho Mail's free tier supports up to 5 email addresses with SMTP access — more than enough for confirmation and unsubscribe mail. `hello@qubitlogic.dev` runs on a Zoho free account.

{{< affiliate_box
    name="Zoho Mail"
    url="AFFILIATE_LINK_ZOHO"
    cta="Start free"
    offer="Free up to 5 users · SMTP included"
    badge="Newsletter email"
    desc="Free business email for your domain — SMTP for transactional mail (confirmations, unsubscribes) and a webmail interface. No credit card for the free tier. Zoho affiliate programme: 15% recurring for 12 months."
    price="Free tier; paid from ~$1/user/mo"
>}}

Sign up at [zoho.com/mail](https://www.zoho.com/mail/), verify your domain via DNS TXT record, create `hello@yourdomain.dev`, and generate an **App Password** for SMTP.

> **Cursor prompt used:**
> *"Review this FastAPI newsletter endpoint for security issues. Check for: SQL injection (are parameters properly escaped?), email address validation, rate limiting on the subscribe endpoint, token entropy, and whether the unsubscribe endpoint leaks subscriber existence."*

---

## Step 15 — Affiliate Links Done Properly

If you monetise with affiliate links, the technical implementation matters for both SEO compliance (Google requires `rel="sponsored"`) and legal compliance (FTC/ASA require clear labelling).

### Central config — one URL to update

Store all affiliate URLs in `hugo.toml`:

```toml
[params.affiliates]
  digitalocean = "https://your-awin-link..."
  vultr        = "https://www.vultr.com/?ref=YOURREF"
  cursor       = "https://cursor.com/referral?code=YOURCODE"
  dynadot      = "https://your-dynadot-referral-link..."
  zoho         = "https://your-zoho-affiliate-link..."
```

### Auto-tagging with a render hook

Create `layouts/_markup/render-link.html`. This runs on every Markdown link and adds `rel="nofollow sponsored noopener"` automatically if the URL matches a known affiliate pattern:

```html
{{- $dest  := .Destination -}}
{{- $rel   := site.Params.affiliate_link_rel | default "nofollow sponsored noopener" -}}
{{- $isAffiliate := false -}}

{{- range site.Params.affiliates -}}
  {{- if and . (in $dest .) -}}{{- $isAffiliate = true -}}{{- end -}}
{{- end -}}

{{- if not $isAffiliate -}}
  {{- if or (in $dest "awin1.com") (in $dest "cursor.com/referral") -}}
    {{- $isAffiliate = true -}}
  {{- end -}}
{{- end -}}

<a href="{{ $dest | safeURL }}"
  {{- if $isAffiliate }} rel="{{ $rel }}" target="_blank"{{- end -}}
  {{- with .Title }} title="{{ . }}"{{- end -}}
>{{ .Text | safeHTML }}</a>
```

> **Cursor prompt used:**
> *"Write a Hugo render-link partial that automatically detects affiliate URLs and adds rel='nofollow sponsored noopener'. It should check two sources: the values in site.Params.affiliates (from hugo.toml), and a manual list of known patterns like awin1.com, cursor.com/referral, and vultr.com with a ref= parameter. Non-affiliate links should render as normal anchor tags."*

---

## Affiliate Opportunities in This Stack

Every tool in this build either has a programme you can apply to now, or is editorial-only (no commission available):

| Tool | Programme | Terms | Apply |
|:---|:---|:---|:---|
| **Cursor** | Referral | Credits/rewards per sign-up | [cursor.com/referral](https://cursor.com/referral?code=TKHKBWB8304Q) — already in hugo.toml |
| **DigitalOcean** | Awin | $25 per qualified referral | [Awin → DigitalOcean](https://ui.awin.com/publisher-signup) |
| **Vultr** | Direct referral | $100 per verified referral | [vultr.com/affiliates](https://www.vultr.com/affiliates/) |
| **Dynadot** | Ambassador (in-house) | 30% domain reg/transfer | [dynadot.com/affiliate](https://www.dynadot.com/affiliate) |
| **Zoho** | Direct | 15–20% recurring for 12 months, 90-day cookie | [zoho.com/affiliate](https://www.zoho.com/affiliate/) |
| Hugo | None — open source | — | — |
| GitHub | None | — | — |
| Cloudflare | None (free product) | — | — |
| Let's Encrypt | None — non-profit | — | — |
| PaperMod | None — open source | — | — |
| Ubuntu | None | — | — |

Dynadot and Zoho are natural fits in a "build a blog" article. Apply at [dynadot.com/affiliate](https://www.dynadot.com/affiliate) and the Zoho affiliate portal before publishing, then paste tracking URLs into `hugo.toml` as `dynadot` and `zoho`.

---

## Total Cost Breakdown

| Item | Monthly | Annual |
|:---|:---|:---|
| VPS — $6/mo plan (DigitalOcean or Vultr) | ~$6 | ~$72 |
| Domain — qubitlogic.dev (registrar) | — | ~£10 |
| Cursor | Free tier | — |
| Hugo, PaperMod, Nginx, FastAPI, SQLite | Free | Free |
| GitHub + GitHub Actions (under 2,000 min/mo) | Free | Free |
| Cloudflare DNS, SSL | Free | Free |
| Zoho Mail | Free | Free |
| Let's Encrypt | Free | Free |
| **Total** | **~$6/mo** | **~$82/yr** |

---

## How Cursor Changed the Workflow

Honest summary of where it saved the most time:

**Hugo templates** — Hugo's templating language has non-obvious scoping rules (`{{ with }}`, `{{ range }}`, context passing). Describing what I wanted in plain English and getting a working draft beats reading documentation for every edge case.

**GitHub Actions YAML** — YAML indentation bugs and Actions-specific syntax are tedious to debug at midnight. Cursor understood what I was trying to do and suggested the fix, not just the syntax.

**CSS components** — describing a visual component ("pill badge, top-left, green, uppercase, 0.68rem") and getting working CSS is faster than writing it from scratch. I tweaked and refined; I didn't type the first draft.

**Security review** — pasting a FastAPI endpoint and asking "what are the security issues here?" catches things a tired solo builder misses (token entropy, SQL injection patterns, rate limiting).

**Compliance writing** — drafting a GDPR privacy policy from a description of your data flows is something Cursor handles well. I reviewed it, made it accurate, had a lawyer friend glance at it. Don't publish compliance documents without a human review, but Cursor gets you to 80% in 10 minutes.

The workflow in practice: write or describe what you want in the chat panel (with the relevant file open), review the output, edit and refine, commit. The integrated terminal means the full loop — edit, test `hugo server`, commit, push, live — never leaves the same window.

---

## The `.cursorrules` File for a Hugo Project

Every competing tutorial that mentions `.cursorrules` shows a generic example. Here is the actual Hugo-specific rules file used for this project. Drop it in your repository root as `.cursorrules`:

```
# QubitLogic — Cursor rules for Hugo + PaperMod

## Project context
- Hugo v0.162+ (extended), theme: PaperMod (themes/PaperMod/)
- All content in content/ as Markdown with YAML front matter
- Custom layouts in layouts/ override PaperMod defaults — always check layouts/ before editing themes/
- Custom shortcodes in layouts/shortcodes/
- Custom CSS in assets/css/extended/ (auto-merged by PaperMod)

## Hugo templating rules — follow these exactly
- Variable scoping: use `{{ $var := . }}` at the top of `{{ with }}` / `{{ range }}` blocks to capture context
- Accessing site params inside range: use `{{ site.Params.foo }}` not `{{ .Site.Params.foo }}`
- Shortcode params: always named, never positional — use `name="value"` pairs, not positional arguments
- Front matter: YAML only. Required fields: title, date, draft, description, tags, categories
- Date format: `2026-06-04T18:00:00+01:00` — always include timezone offset

## Content rules
- Article descriptions: max 155 characters, keyword first, no full stops at end
- All outbound affiliate links must use the `affiliate_link` or `affiliate_box` shortcodes
- All affiliate links get `rel="nofollow sponsored noopener"` — this is handled by the shortcodes, never add manually
- Internal links: use root-relative paths (`/infrastructure/my-article/`) not full URLs

## Do not
- Do not edit anything in themes/ — override in layouts/ instead
- Do not add `<script>` or `<style>` tags inline in Markdown
- Do not use `{{ .Site.Params }}` — use `{{ site.Params }}` (Hugo v0.113+ syntax)
- Do not create new shortcodes without adding them to layouts/shortcodes/
```

> **Why this works:** giving Cursor your exact Hugo version, theme name, and the two most common gotchas (variable scoping and `site.Params` vs `.Site.Params`) eliminates the most frequent hallucinations. The "do not edit themes/" rule prevents Cursor from writing changes that get overwritten on theme updates.

---

## Deep-dive infrastructure guides

This build log is the narrative; these standalone tutorials have the copy-paste commands:

| Topic | Guide |
|-------|-------|
| VPS security baseline | [Ubuntu 24.04 hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/) |
| Hugo CI/CD deploy | [GitHub Actions + rsync](/infrastructure/deploy-hugo-github-actions-vps/) |
| Newsletter API | [FastAPI + SQLite](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/) |
| Cloudflare edge | [Static site + API](/infrastructure/cloudflare-nginx-vps-static-site-api/) |
| FastAPI production | [Nginx + systemd + SSL](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) |

---

## Getting Started Today

1. **[Install Cursor](https://cursor.com/referral?code=TKHKBWB8304Q)** — free tier is enough to start
2. **Register a domain** — [Dynadot](https://www.dynadot.com/) + Cloudflare nameservers
3. **[Harden a VPS](/infrastructure/secure-ubuntu-24-04-vps-hardening/)** then [provision it](/infrastructure/how-to-provision-vps-ai-agent-workloads/) — DigitalOcean or Vultr
4. **Install Hugo** and clone PaperMod
5. **Design your logo** in SVG with Cursor — describe it, iterate, done
6. **[Set up GitHub Actions deploy](/infrastructure/deploy-hugo-github-actions-vps/)** — push to main, site updates
7. **Harden Nginx** with security headers
8. **Write your privacy policy and affiliate disclosure** before going live
9. **[Build the newsletter API](/infrastructure/self-hosted-newsletter-api-fastapi-sqlite/)** when ready — or start with Zoho forwarding

The whole stack can be running in a weekend. The hard part is not the infrastructure — it is writing consistently once it is live.

---

## Frequently Asked Questions

**Why Hugo over WordPress for a technical blog?**
WordPress is a PHP application that requires a database, a runtime server, and constant plugin updates. Hugo generates static HTML — there is no attack surface at runtime, no CMS to patch, and pages load faster because they are plain files served by Nginx. For a developer writing in Markdown with Git, Hugo fits the workflow; WordPress does not.

**Is Hugo harder to use than Astro for AI-assisted development?**
In practice, no. The 2026 argument that Astro is easier for LLMs is accurate in theory (more JSX training data), but Cursor handles Hugo templates well when you give it context. The limiting factor is usually writing clear prompts, not the framework. Hugo wins on operational simplicity: one Go binary, no Node toolchain, sub-second builds.

**How much does this stack cost per month?**
About **$6–8/month** (VPS) plus roughly **£10/year** for the domain. Everything else — Hugo, GitHub Actions, Cloudflare, Let's Encrypt, Cursor free tier, Zoho Mail free tier — is free.

**Do I need to know Go to use Hugo?**
No. Hugo's templating language looks like Go but is a simplified subset. You will learn the basics (`{{ .Title }}`, `{{ range }}`, `{{ with }}`) as you customise a theme. Cursor is particularly useful here: describe what you want the template to do and it drafts the syntax.

**Can I build this without Cursor?**
Yes — the stack is framework-agnostic and the GitHub Actions workflow, Hugo config, and FastAPI code work in any editor. Cursor is recommended because it speeds up the parts most developers find tedious: template syntax, YAML pipelines, and compliance writing.

**How long does the whole build take?**
Realistically **one to two weekends** for the full stack: domain, VPS, Hugo site, GitHub Actions deploy, newsletter API, and compliance pages. Writing the first batch of articles takes longer than building the infrastructure.

**What is the best Cursor prompt for Hugo?**
*"I am using Hugo with the PaperMod theme. Here is my current `layouts/` folder structure. Write a shortcode that [describe what you need] — use Go template syntax and explain any scoping quirks."* Giving Cursor your folder structure and theme name upfront eliminates most hallucinated syntax.

---

{{< affiliate_stack >}}

{{< affiliate_box
    name="Cursor"
    url="AFFILIATE_LINK_CURSOR"
    cta="Try Cursor free"
    offer="Referral link · free tier to start"
    badge="AI-assisted IDE"
    primary="true"
    desc="Every file in this build — Hugo templates, GitHub Actions, CSS, FastAPI, the SVG logo — was written or refined in Cursor. The chat panel that understands your whole codebase changes the workflow."
    price="Free tier; paid plans available"
>}}

---

*Have questions about any part of this stack? The [QubitLogic newsletter](/newsletter/) goes out weekly — or open an issue on the [GitHub repo](https://github.com/stephanepatteux/QubitLogic).*
