# QubitLogic

**Quantum computing · AI infrastructure · Python development**

Technical articles with reproducible code, honest benchmarks, and practical implementation guides.

🌐 [qubitlogic.dev](https://qubitlogic.dev)

---

## Content

| Section | Focus |
|---|---|
| [Infrastructure](/content/infrastructure/) | VPS provisioning, Nginx, Python, CI/CD |
| [Quantum Coding](/content/quantum-coding/) | Qiskit, QAOA, Grover's, hybrid ML |
| [Professional Edge](/content/professional-edge/) | PQC, RAG agents, financial APIs, compliance |

## Built with

- [Hugo](https://gohugo.io/) static site generator (v0.162.1 Extended)
- [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme
- Deployed via GitHub Actions to a self-hosted VPS with Nginx + Let's Encrypt

## Running locally

```bash
git clone --recurse-submodules https://github.com/stephanepatteux/QubitLogic.git
cd QubitLogic
bash scripts/setup-dev.sh   # one-time: submodules, Hugo, Pillow
hugo server -D
```

Open [http://localhost:1313](http://localhost:1313).

## Newsletter

Self-hosted newsletter system — no third-party service.

| Component | Description |
|---|---|
| `newsletter/api.py` | FastAPI subscribe / confirm / unsubscribe API (port 8001) |
| `newsletter/send.py` | Weekly RSS → SMTP send script |
| `newsletter/test_send.py` | One-off test send to a single address |
| `.github/workflows/newsletter.yml` | Cron (Tue 09:00 UTC) + manual dispatch with `dry-run`, `test-send`, `force-send`, `setup-api` modes |

Required GitHub secrets: `VPS_SSH_KEY`, `SMTP_PASSWORD`.

See [deploy-notes.md](./deploy-notes.md) for full VPS setup and service management.

## CI/CD

| Workflow | Trigger | What it does |
|---|---|---|
| `deploy.yml` | Push to `main` | Hugo build → rsync site + newsletter scripts to VPS |
| `newsletter.yml` | Tuesday 09:00 UTC / manual | Newsletter send + VPS setup modes |

## License

Article content © 2026 Stephane Patteux, licensed under
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) —
share with attribution, no commercial use.

Code snippets in articles are released under the MIT License.

See [LICENSE](./LICENSE) for full details.
