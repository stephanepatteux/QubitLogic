---
# DEV.to — paste front matter when publishing
title: "Deploy LangChain on a VPS — Production Setup (FastAPI + systemd + Nginx)"
published: false
description: Stop running LangChain in tmux. Deploy a ReAct agent behind Gunicorn, systemd, and Nginx on Ubuntu 24.04 with secure API key handling.
tags: langchain, python, devops, ai
canonical_url: https://qubitlogic.dev/infrastructure/deploy-langchain-on-vps-ubuntu-24-04/
cover_image: https://qubitlogic.dev/images/og/deploy-langchain-on-vps-ubuntu-24-04.png
---

> **Full walkthrough with every config file:** [qubitlogic.dev/infrastructure/deploy-langchain-on-vps-ubuntu-24-04/](https://qubitlogic.dev/infrastructure/deploy-langchain-on-vps-ubuntu-24-04/)

`python agent.py` in a `tmux` session is not production. Here's the stack I use for LangChain agents on a $12–24/mo VPS:

| Layer | Tool |
|:---|:---|
| App | FastAPI + LangChain ReAct agent |
| Process | Gunicorn + UvicornWorker |
| Supervision | systemd (`Restart=always`) |
| Edge | Nginx + Certbot TLS |

## Minimum VPS

**2 vCPU / 4 GB RAM** — see [best VPS comparison](https://qubitlogic.dev/infrastructure/best-vps-for-ai-agents-2026/) for provider picks.

## Secrets — never in git

```bash
sudo tee /etc/agent.env << 'EOF'
OPENAI_API_KEY=sk-your-key-here
AGENT_MODEL=gpt-4o-mini
EOF
sudo chmod 600 /etc/agent.env
```

Reference: [LangChain environment variables](https://python.langchain.com/docs/how_to/#environment-variables)

## systemd unit (critical bits)

```ini
EnvironmentFile=/etc/agent.env
ExecStart=/opt/agent/venv/bin/gunicorn main:app \
    -k uvicorn.workers.UvicornWorker -w 2 -b 127.0.0.1:8000 \
    --timeout 300
Restart=always
```

**`--timeout 300`** — default 30s kills multi-step ReAct loops. Match Nginx `proxy_read_timeout 300s`.

## Nginx — never expose port 8000

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_read_timeout 300s;
}
```

UFW should allow **22, 80, 443 only** — not 8000.

Official refs: [FastAPI deployment](https://fastapi.tiangolo.com/deployment/), [FastAPI behind a proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/)

## Production checklist

- [ ] `systemctl is-active langchain-agent` after reboot
- [ ] HTTPS via Certbot
- [ ] API key not in `/opt/agent` source
- [ ] CI/CD via [GitHub Actions](https://qubitlogic.dev/infrastructure/cicd-pipeline-ai-python-scripts/)

**Full code (FastAPI app, systemd, Nginx, troubleshooting):** **[Deploy LangChain on a VPS](https://qubitlogic.dev/infrastructure/deploy-langchain-on-vps-ubuntu-24-04/)**

Related:
- [Ubuntu 24.04 hardening first](https://qubitlogic.dev/infrastructure/secure-ubuntu-24-04-vps-hardening/)
- [Enterprise RAG on VPS](https://qubitlogic.dev/professional-edge/integrating-enterprise-rag-agents/)

---

*Cross-posted from [QubitLogic](https://qubitlogic.dev/) — infrastructure tutorials with runnable code.*
