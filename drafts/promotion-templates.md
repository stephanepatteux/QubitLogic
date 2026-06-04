# Promotion templates for: How to Build a Technical Blog with Cursor and Hugo (2026)

Article URL: https://qubitlogic.dev/build-technical-blog-cursor-hugo/

---

## Google Search Console

Manual indexing request — do this first, takes 30 seconds:
1. Go to https://search.google.com/search-console
2. Paste each URL below into the URL inspection bar → click "Request Indexing":
   - https://qubitlogic.dev/build-technical-blog-cursor-hugo/
   - https://qubitlogic.dev/start-here/
   - https://qubitlogic.dev/quantum-developer-toolkit/
   - https://qubitlogic.dev/about/
   - https://qubitlogic.dev/infrastructure/cicd-pipeline-ai-python-scripts/
   - https://qubitlogic.dev/infrastructure/nginx-reverse-proxy-python-ai-api/

---

## Hacker News — Show HN

**Title (pick one — keep under 80 chars):**
```
Show HN: I built a technical blog with Cursor and Hugo for under £10/mo
```
```
Show HN: Full stack for a technical blog – Hugo, VPS, self-hosted newsletter, GDPR
```

**Post body (paste in the text field, or leave blank — HN often prefers no body for Show HN):**
```
Built QubitLogic from scratch using Cursor as the editor throughout.

Stack: Hugo + PaperMod → GitHub Actions → rsync to a $6/mo VPS running Nginx. 
Self-hosted FastAPI newsletter API with SQLite and Zoho Mail for transactional email.

The article covers the bits most "how to blog" tutorials skip: the SVG logo 
designed with Cursor, Nginx security headers, UK GDPR compliance pages, and the 
actual .cursorrules file that keeps Cursor from hallucinating Hugo template syntax.

Full article: https://qubitlogic.dev/build-technical-blog-cursor-hugo/
```

**Where to post:** https://news.ycombinator.com/submit
**Best time:** Tuesday–Thursday, 9–11am US Eastern

---

## Reddit

### r/selfhosted
**Title:**
```
Self-hosted technical blog with Hugo + FastAPI newsletter on a $6/mo VPS — full build log including GDPR compliance and Nginx security headers
```
**Body:**
```
Built QubitLogic and wrote up the full stack — Hugo static site, PaperMod theme, 
self-hosted newsletter API (FastAPI + SQLite + Zoho Mail for SMTP), automated 
GitHub Actions deploy to a VPS, Nginx security headers.

The article includes: SVG logo with Cursor, GDPR/UK privacy compliance, 
.cursorrules file for Hugo, and a VPS vs GitHub Pages cost comparison.

https://qubitlogic.dev/build-technical-blog-cursor-hugo/
```

### r/webdev
**Title:**
```
How I built a technical blog with Cursor and Hugo in 2026 — full stack including self-hosted newsletter, GDPR compliance, and the .cursorrules file I use
```
**Body:**
```
Wrote up the complete build log for QubitLogic. Main differentiation vs other 
"Hugo blog" tutorials: this one uses a VPS (not GitHub Pages) to support a 
self-hosted newsletter API, covers UK GDPR compliance properly, and includes the 
actual Cursor prompts used at each step.

Stack: Hugo + PaperMod + GitHub Actions + rsync deploy + FastAPI + SQLite + Zoho Mail + Certbot

https://qubitlogic.dev/build-technical-blog-cursor-hugo/
```

### r/cursor_ai (or r/ChatGPT/r/AIAssistants)
**Title:**
```
The .cursorrules file I use for Hugo projects — eliminates the most common hallucinations
```
**Body:**
```
Been building a technical blog with Cursor and Hugo. The biggest friction was 
Cursor hallucinating Hugo syntax (wrong scoping in range blocks, old .Site.Params 
syntax vs site.Params, etc.).

Wrote up the exact .cursorrules file that fixed this, along with the full build 
log for the site. The rules file is about halfway down the article.

https://qubitlogic.dev/build-technical-blog-cursor-hugo/
```

### r/hugo (if it exists) / r/gohugo
**Title:**
```
Build log: Hugo + PaperMod + self-hosted newsletter + .cursorrules for AI editing — what I learned
```
**Body:**
```
Built a technical blog on Hugo with PaperMod. Key things I didn't find good 
documentation for elsewhere:

1. The .cursorrules file that keeps AI editors from making Go template mistakes
2. VPS deploy via GitHub Actions + rsync (not GitHub Pages)
3. Self-hosted newsletter with FastAPI + SQLite on the same VPS
4. Auto-inserting rel="sponsored nofollow" on affiliate links via a render-link hook

Full article with code: https://qubitlogic.dev/build-technical-blog-cursor-hugo/
```

---

## LinkedIn (personal post)

```
I spent a weekend building QubitLogic from scratch and wrote up the full stack.

The bits most tutorials skip:
→ Designing the SVG logo in Cursor with a single prompt
→ GDPR / UK compliance before going live (required, not optional)
→ Self-hosted newsletter with FastAPI + SQLite instead of paying Mailchimp
→ Nginx security headers (A+ on securityheaders.com)
→ The .cursorrules file that keeps AI from hallucinating Hugo syntax

Total cost: ~$6/month VPS + £10/year domain. Everything else is free.

Full build log: https://qubitlogic.dev/build-technical-blog-cursor-hugo/

#cursor #hugo #devops #buildinpublic
```

---

## X / Twitter thread opener

```
I built a technical blog with @cursor_ai and Hugo from scratch.

Here's the full stack — including the bits other tutorials skip:

🧵 Thread (1/8)
```

Follow-up tweets:
1. Stack overview table (screenshot)
2. Why VPS over GitHub Pages (3 bullet points)
3. The SVG logo designed with a single Cursor prompt
4. GDPR compliance setup
5. Self-hosted newsletter API (FastAPI + SQLite)
6. The .cursorrules file
7. Total cost breakdown
8. Link to full article

---

## DEV.to / Hashnode

Use the draft at: drafts/devto-hashnode-draft.md

Steps:
1. Go to dev.to/new (or hashnode.com)
2. Paste the content from drafts/devto-hashnode-draft.md
3. The canonical_url in the front matter points back to qubitlogic.dev — this is critical
4. Publish — DEV.to will respect the canonical and Google will count it as a backlink to QubitLogic, not as duplicate content
