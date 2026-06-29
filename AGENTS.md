# AGENTS.md

Guidance for AI agents working in this repository.

## Cursor Cloud specific instructions

### What this repo is

QubitLogic is a **Hugo Extended** static site (PaperMod theme via git submodule). There is no `package.json`, Python app, Docker Compose, or project-level lint/test suite. Local development is Hugo only.

### Prerequisites

- **Hugo Extended v0.162.1+** (matches `.github/workflows/deploy.yml`). The Cloud VM image may already include it at `/usr/local/bin/hugo`; verify with `hugo version`.
- **PaperMod submodule**: builds fail if `themes/PaperMod` is empty. After every fresh clone or pull that might change submodules, run `git submodule update --init --recursive`.

### Commands (see also `README.md` / `CONTRIBUTING.md`)

| Task | Command |
|------|---------|
| Dev server | `hugo server -D --bind 0.0.0.0 --baseURL http://127.0.0.1:1313/` |
| Production build | `hugo --minify` → `public/` |
| Lint / unit tests | Not defined in this repo |

### Running the dev server

Use a **tmux** session (e.g. `hugo-dev-server`) so the server survives backgrounding:

```bash
hugo server -D --bind 0.0.0.0 --baseURL http://127.0.0.1:1313/
```

Default URL: [http://localhost:1313](http://localhost:1313). Hugo live-reloads on content/layout changes; no app restart needed for typical edits.

### Gotchas

- **Submodule first**: If `hugo` errors about missing theme files, run `git submodule update --init --recursive` before rebuilding.
- **No secrets for local dev**: Hugo does not read a `.env` for site builds. Deploy secrets (`VPS_SSH_KEY`, etc.) are GitHub Actions only.
- **Beehiiv / third-party scripts**: Newsletter embeds load from Beehiiv CDN in the browser; they are optional for core content editing.
- **CI deploy**: Pushing to `main` triggers `.github/workflows/deploy.yml` (build + `rsync` to VPS). Do not push to `main` unless deployment is intended.

### Smoke test (hello world)

1. `hugo --minify` succeeds.
2. `hugo server -D` serves HTTP 200 on `/`.
3. Browse **Quantum Coding** → open an article; use **Search** with a term like `quantum` to confirm client-side search.
