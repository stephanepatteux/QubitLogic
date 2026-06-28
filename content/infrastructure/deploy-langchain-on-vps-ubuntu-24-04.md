---
aliases:
  - /deploy-langchain-on-vps/
  - /how-to-deploy-ai-agent-on-vps/
title: "Deploy LangChain on a VPS: Production Setup for Ubuntu 24.04"
seoTitle: "Deploy LangChain on a VPS (2026)"
date: 2026-06-28T09:00:00+01:00
lastmod: 2026-06-28T09:00:00+01:00
draft: false
description: "Deploy LangChain on a VPS with FastAPI, Gunicorn, systemd, and Nginx — production-ready Ubuntu 24.04 setup with env secrets, health checks, and LLM timeout tuning."
keywords:
  - "deploy langchain on vps"
  - "how to deploy ai agent on vps"
  - "run ai agent on vps"
  - "langchain production deployment"
  - "langchain fastapi vps"
  - "ai agent vps setup guide"
summary: "Running LangChain on your laptop is not production. This guide deploys a ReAct agent behind FastAPI + Gunicorn + systemd + Nginx on Ubuntu 24.04 — the same stack we use across QubitLogic infrastructure tutorials."

series: ["Phase 1: Infrastructure"]
tags: ["langchain", "python", "fastapi", "vps", "ubuntu", "nginx", "systemd", "ai-agents", "infrastructure"]
categories: ["tutorial"]

images: ["/images/og/deploy-langchain-on-vps-ubuntu-24-04.png"]

faq:
  - q: "How do I deploy LangChain on a VPS?"
    a: "Install Python 3.11+, create a venv with langchain and fastapi, bind Gunicorn with UvicornWorker to 127.0.0.1:8000, manage with systemd, and put Nginx in front for TLS. Store OPENAI_API_KEY in /etc/environment or a root-only .env file — never in git."
  - q: "What VPS specs do I need for LangChain?"
    a: "Minimum: 2 vCPU, 4 GB RAM, 50 GB NVMe (~$12/mo). That handles one ReAct agent with tool calls and a small SQLite cache. See our best VPS comparison for provider picks."
  - q: "Should LangChain run in Docker on a VPS?"
    a: "For a single agent on a $12/mo VPS, systemd + Gunicorn is simpler and uses less RAM than Docker. Docker makes sense when you run five+ services; for one API, native systemd is the right default per FastAPI deployment docs."
  - q: "How do I keep API keys secure on a VPS?"
    a: "Use EnvironmentFile in systemd pointing to /etc/agent.env (chmod 600, owned by root). Never commit keys to GitHub. Rotate keys if exposed. See LangChain security best practices in their official docs."

weight: 2
ShowToc: true
howto_total_time: "PT60M"
howto_cost: "12"
---

{{< callout type="tip" title="Quick answer — deploy LangChain on a VPS" >}}
**2 vCPU / 4 GB RAM VPS** → harden Ubuntu → Python venv with LangChain → FastAPI wrapper → **Gunicorn on 127.0.0.1:8000** → **systemd** auto-restart → **Nginx + Certbot** for HTTPS. Never expose uvicorn directly. Full stack: [FastAPI deploy](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) + [Nginx hardening](/infrastructure/nginx-reverse-proxy-python-ai-api/).
{{< /callout >}}

## Overview

If you want to **run an AI agent on a VPS** or **deploy LangChain on a VPS** in production, you need more than `python agent.py` in a `tmux` session. Production means:

- Process supervision (systemd restarts on crash)
- TLS termination (Nginx + [Let's Encrypt](https://letsencrypt.org/))
- Secrets outside the codebase ([LangChain env var docs](https://python.langchain.com/docs/how_to/#environment-variables))
- Timeouts tuned for slow LLM responses

This guide builds a minimal but production-grade LangChain ReAct agent behind FastAPI — the same architectural pattern used in our [enterprise RAG guide](/professional-edge/integrating-enterprise-rag-agents/) and [agentic workflows benchmark](/professional-edge/agentic-workflows-vs-manual-scripts/).

**Prerequisites:**

- Ubuntu 24.04 VPS (2 vCPU / 4 GB RAM) — see [best VPS for AI agents](/infrastructure/best-vps-for-ai-agents-2026/) to pick a provider
- [Hardening complete](/infrastructure/secure-ubuntu-24-04-vps-hardening/) — non-root user, UFW, SSH keys
- OpenAI or Anthropic API key

{{< affiliate_stack >}}

---

## Step 1 — System Packages and Python Environment

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip git

sudo mkdir -p /opt/agent
sudo chown deploy:deploy /opt/agent
cd /opt/agent

python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install \
    "langchain>=0.3" \
    "langchain-openai>=0.2" \
    "langchain-community>=0.3" \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.32" \
    "gunicorn>=23.0" \
    python-dotenv
```

Store secrets in a root-only env file (never commit this):

```bash
sudo tee /etc/agent.env << 'EOF'
OPENAI_API_KEY=sk-your-key-here
AGENT_MODEL=gpt-4o-mini
EOF
sudo chmod 600 /etc/agent.env
sudo chown root:root /etc/agent.env
```

---

## Step 2 — Minimal LangChain Agent + FastAPI App

Create `/opt/agent/main.py`:

```python
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain import hub


@tool
def word_count(text: str) -> str:
    """Count words in a string."""
    return str(len(text.split()))


@tool
def reverse_text(text: str) -> str:
    """Reverse a string."""
    return text[::-1]


tools = [word_count, reverse_text]
prompt = hub.pull("hwchase17/react")
llm = ChatOpenAI(
    model=os.getenv("AGENT_MODEL", "gpt-4o-mini"),
    temperature=0,
)
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=8)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    answer: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="LangChain Agent API", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "model": os.getenv("AGENT_MODEL", "gpt-4o-mini")}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    try:
        result = await executor.ainvoke({"input": req.question})
        return QueryResponse(answer=result["output"])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

Test locally before systemd:

```bash
cd /opt/agent && source venv/bin/activate
set -a && source /etc/agent.env && set +a
gunicorn main:app -k uvicorn.workers.UvicornWorker -w 2 -b 127.0.0.1:8000
```

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How many words in hello world?"}'
```

---

## Step 3 — systemd Service

Create `/etc/systemd/system/langchain-agent.service`:

```ini
[Unit]
Description=LangChain Agent API (Gunicorn + Uvicorn)
After=network.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/opt/agent
EnvironmentFile=/etc/agent.env
ExecStart=/opt/agent/venv/bin/gunicorn main:app \
    -k uvicorn.workers.UvicornWorker \
    -w 2 \
    -b 127.0.0.1:8000 \
    --timeout 300 \
    --graceful-timeout 30
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now langchain-agent
sudo systemctl status langchain-agent
journalctl -u langchain-agent -f
```

{{< callout type="warning" title="LLM timeouts" >}}
Default Gunicorn timeout is 30s — too short for multi-step ReAct loops. We set `--timeout 300`. Match Nginx `proxy_read_timeout` in the [Nginx hardening guide](/infrastructure/nginx-reverse-proxy-python-ai-api/).
{{< /callout >}}

---

## Step 4 — Nginx Reverse Proxy + TLS

Install Nginx and Certbot (full walkthrough: [Deploy FastAPI on Ubuntu 24.04](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/)):

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

`/etc/nginx/sites-available/agent`:

```nginx
server {
    listen 80;
    server_name agent.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/agent /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d agent.yourdomain.com
```

Verify HTTPS:

```bash
curl -s https://agent.yourdomain.com/health
```

Official references: [FastAPI behind a proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/), [Nginx reverse proxy docs](https://nginx.org/en/docs/http/ngx_http_proxy_module.html).

---

## Step 5 — Firewall and Reboot Test

```bash
sudo ufw status   # should show 22, 80, 443 only — NOT 8000
sudo reboot
# after reboot:
curl -s https://agent.yourdomain.com/health
```

Port 8000 must **not** be public. Only Nginx reaches Gunicorn on localhost.

---

## Production Checklist

| Check | Command / action |
|:---|:---|
| Agent survives reboot | `systemctl is-active langchain-agent` |
| HTTPS works | `curl -I https://agent.yourdomain.com/health` |
| Port 8000 closed externally | `sudo ufw status` |
| Logs rotate | `journalctl -u langchain-agent --since today` |
| API key not in git | `grep -r sk- /opt/agent` → empty |
| CI/CD deploy | [GitHub Actions pipeline](/infrastructure/cicd-pipeline-ai-python-scripts/) |

---

## Scaling Beyond One Agent

| Need | Next step |
|:---|:---|
| Vector memory / RAG | [Enterprise RAG guide](/professional-edge/integrating-enterprise-rag-agents/) |
| Local models (no API cost) | [Ollama on VPS](/infrastructure/self-hosted-ai-agent-ollama-vps-2026/) |
| Multi-agent orchestration | Upgrade to 4 vCPU / 8 GB — [best VPS guide](/infrastructure/best-vps-for-ai-agents-2026/) |
| Monitoring | [Uptime Kuma](/infrastructure/uptime-kuma-monitoring-ubuntu-vps-24-04/) |

---

## Common Failures

| Symptom | Fix |
|:---|:---|
| 504 Gateway Timeout | Raise Gunicorn `--timeout` and Nginx `proxy_read_timeout` to 300s |
| OOM kill | Reduce Gunicorn workers (`-w 1` on 2 GB RAM) or upgrade VPS |
| `OPENAI_API_KEY` not found | Check `EnvironmentFile=/etc/agent.env` in systemd unit |
| Agent works locally, fails in systemd | Verify `User=deploy` owns `/opt/agent` |

---

## Conclusion

**Deploy LangChain on a VPS** by treating it like any production Python API: Gunicorn + systemd + Nginx, secrets in `/etc/agent.env`, and timeouts tuned for LLM latency. This pattern scales from a single ReAct agent to the RAG pipelines in Phase 3.

{{< affiliate_box
    name="DigitalOcean"
    url="AFFILIATE_LINK_DIGITALOCEAN"
    cta="Deploy Agent VPS"
    badge="Recommended"
    desc="2 vCPU / 4 GB Premium AMD Droplet — enough for LangChain + FastAPI + Nginx with headroom for tool calls."
    price="From $24/mo"
>}}

**→ Related:** [Best VPS for AI Agents (2026)](/infrastructure/best-vps-for-ai-agents-2026/) · [Provision + benchmark](/infrastructure/how-to-provision-vps-ai-agent-workloads/)

*Part of [Phase 1: Infrastructure](/infrastructure/) — [See the full learning path](/start-here/)*
