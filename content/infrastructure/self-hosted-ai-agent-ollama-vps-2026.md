---
aliases:
  - /self-hosted-ai-agent/
  - /ollama-on-vps/
title: "Self-Hosted AI Agent on a VPS: Ollama + FastAPI Stack (2026)"
seoTitle: "Self-Hosted AI Agent on VPS (Ollama)"
date: 2026-06-28T10:00:00+01:00
lastmod: 2026-06-28T10:00:00+01:00
draft: false
description: "Run a self-hosted AI agent on a VPS with Ollama, FastAPI, and Nginx — local Llama 3 / Mistral inference without OpenAI API costs. Ubuntu 24.04 production setup."
keywords:
  - "self hosted ai agent"
  - "ollama vps"
  - "run ollama on vps"
  - "local llm vps"
  - "self hosted llm agent"
  - "ollama ubuntu 24.04"
summary: "API-based agents send data to third parties and bill per token. This guide runs Ollama on a VPS with a FastAPI wrapper, systemd, and Nginx — a fully self-hosted AI agent stack from $12/mo with no inference API fees."

series: ["Phase 1: Infrastructure"]
tags: ["ollama", "self-hosted", "vps", "fastapi", "ubuntu", "ai-agents", "llm", "infrastructure"]
categories: ["tutorial"]

images: ["/images/og/self-hosted-ai-agent-ollama-vps-2026.png"]

faq:
  - q: "Can I run Ollama on a VPS?"
    a: "Yes. Install Ollama on Ubuntu 24.04, pull a model (e.g. llama3.2:3b or mistral:7b), and wrap it with FastAPI + Nginx. Minimum 8 GB RAM for 7B models on CPU. GPU instances are faster but cost more — CPU inference is viable for low-traffic agents."
  - q: "How much RAM do I need for Ollama on a VPS?"
    a: "3B models: 4–8 GB RAM. 7–8B models: 8 GB minimum. 13B: 16 GB. 70B quantized: 48 GB+. Check ollama.com/library for each model's requirements. Hetzner CX32 (8 GB) or Vultr 8 GB plan are common starting points."
  - q: "Is a self-hosted AI agent cheaper than OpenAI?"
    a: "For low-volume personal agents, yes — you pay VPS cost only (~$12–24/mo) with no per-token fees. For high-volume production (millions of tokens/day), cloud APIs often win on total cost when you factor in hardware and ops time."
  - q: "How do I expose Ollama safely on a VPS?"
    a: "Never bind Ollama (port 11434) to 0.0.0.0 publicly. Run it on localhost, wrap with FastAPI on 127.0.0.1:8000, and put Nginx + TLS in front. Add rate limiting per the Nginx hardening guide."

weight: 3
ShowToc: true
---

{{< callout type="tip" title="Quick answer — self-hosted AI agent on a VPS" >}}
**8 GB RAM VPS** → install [Ollama](https://ollama.com/) → pull `llama3.2:3b` or `mistral:7b` → FastAPI wrapper on **127.0.0.1:8000** → **Nginx + Certbot** → no OpenAI API key required. Pick hardware: [best VPS for AI agents](/infrastructure/best-vps-for-ai-agents-2026/).
{{< /callout >}}

## Overview

A **self-hosted AI agent** keeps prompts and responses on infrastructure you control. Instead of calling OpenAI on every turn, you run [Ollama](https://github.com/ollama/ollama) locally and wrap it with a thin API layer.

This guide deploys:

| Layer | Role |
|:---|:---|
| **Ollama** | Local LLM inference (Llama, Mistral, Phi, Qwen) |
| **FastAPI** | HTTP API + optional tool routing |
| **Gunicorn + systemd** | Process supervision |
| **Nginx** | TLS, rate limits, never expose Ollama directly |

**When self-hosting makes sense:**

- Privacy-sensitive workflows (internal docs, unreleased code)
- Predictable monthly cost vs spiky API bills
- Offline-capable agents in air-gapped or EU-residency setups

**When cloud APIs win:** high throughput, latest frontier models (GPT-4o, Claude), or sub-second latency at scale. See [LangChain on VPS with OpenAI](/infrastructure/deploy-langchain-on-vps-ubuntu-24-04/) for that path.

---

## Prerequisites

| Requirement | Detail |
|:---|:---|
| VPS | **8 GB RAM minimum** for 7B models — [best VPS comparison](/infrastructure/best-vps-for-ai-agents-2026/) |
| OS | Ubuntu 24.04 LTS |
| Hardening | [SSH + UFW checklist](/infrastructure/secure-ubuntu-24-04-vps-hardening/) complete |
| Domain | Optional but recommended for HTTPS |

{{< affiliate_stack >}}

---

## Step 1 — Install Ollama

Official install ([Ollama Linux docs](https://github.com/ollama/ollama/blob/main/docs/linux.md)):

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama
sudo systemctl start ollama
```

Pull a model sized to your RAM:

```bash
# ~2 GB RAM — good for testing on CX22
ollama pull llama3.2:3b

# ~8 GB RAM — better quality
ollama pull mistral:7b
```

Verify inference:

```bash
ollama run llama3.2:3b "Summarize VPS hardening in one sentence."
```

Benchmark tokens/sec on your hardware:

```bash
time ollama run llama3.2:3b "Write a 100-word paragraph about Python."
```

Expect **4–12 tokens/sec on CPU** for 7B models — acceptable for batch agents, slow for chat UX. [Ollama model library](https://ollama.com/library) lists all available models.

---

## Step 2 — Lock Ollama to Localhost

By default Ollama listens on `127.0.0.1:11434`. Confirm:

```bash
ss -tlnp | grep 11434
# should show 127.0.0.1:11434 — NOT 0.0.0.0
```

If exposed publicly, override in `/etc/systemd/system/ollama.service.d/override.conf`:

```ini
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

{{< callout type="warning" title="Never expose port 11434" >}}
Unauthenticated Ollama instances on the public internet have been abused for crypto mining. Always bind localhost-only and put Nginx + auth in front if you need remote access.
{{< /callout >}}

---

## Step 3 — FastAPI Wrapper

```bash
sudo mkdir -p /opt/ollama-agent
sudo chown deploy:deploy /opt/ollama-agent
cd /opt/ollama-agent
python3.12 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn gunicorn httpx
```

`/opt/ollama-agent/main.py`:

```python
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

app = FastAPI(title="Self-Hosted Ollama Agent")


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    response: str
    model: str


@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{OLLAMA_URL}/api/tags")
        r.raise_for_status()
    return {"status": "ok", "model": MODEL}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    payload = {
        "model": MODEL,
        "prompt": req.prompt,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
        return ChatResponse(response=data["response"], model=MODEL)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
```

Test:

```bash
cd /opt/ollama-agent && source venv/bin/activate
gunicorn main:app -k uvicorn.workers.UvicornWorker -w 1 -b 127.0.0.1:8000 &
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is a VPS?"}'
```

---

## Step 4 — systemd for the API Layer

`/etc/systemd/system/ollama-agent.service`:

```ini
[Unit]
Description=Ollama FastAPI wrapper
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/ollama-agent
Environment="OLLAMA_MODEL=llama3.2:3b"
ExecStart=/opt/ollama-agent/venv/bin/gunicorn main:app \
    -k uvicorn.workers.UvicornWorker -w 1 -b 127.0.0.1:8000 --timeout 300
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ollama-agent
```

---

## Step 5 — Nginx + TLS

Follow [Deploy FastAPI on Ubuntu 24.04](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) for Certbot setup. Add LLM-aware timeouts from [Nginx hardening](/infrastructure/nginx-reverse-proxy-python-ai-api/):

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    limit_req zone=api burst=10 nodelay;
}
```

---

## Model Sizing Reference

| Model | Params | RAM (approx) | CPU tokens/sec | Use case |
|:---|:---|:---|:---|:---|
| llama3.2:3b | 3B | 4 GB | ~12–20 | Dev, low-traffic bots |
| mistral:7b | 7B | 8 GB | ~4–8 | General agent |
| phi3:14b | 14B | 16 GB | ~2–4 | Higher quality |
| llama3.1:70b | 70B | 48 GB+ | ~0.5–1 | Not practical on budget VPS |

Source: [Ollama model tags](https://ollama.com/library) and community benchmarks. Always test on **your** VPS before production.

---

## Self-Hosted vs Cloud API

{{< code_benchmark title="Cost comparison — 100k tokens/day agent (illustrative)" >}}
| Approach | Monthly infra | Inference cost | Ops burden |
|:---|:---|:---|:---|
| OpenAI gpt-4o-mini API | $12 VPS | ~$15–30 API | Low |
| Ollama mistral:7b on VPS | $24 VPS (8 GB) | $0 | Medium |
| Hybrid (Ollama + API fallback) | $24 VPS | Variable | Higher |
{{< /code_benchmark >}}

For hybrid patterns, route simple queries to Ollama and escalate to cloud APIs — see [enterprise RAG architecture](/professional-edge/integrating-enterprise-rag-agents/).

---

## Production Checklist

- [ ] Ollama bound to 127.0.0.1 only
- [ ] UFW allows 22/80/443 — not 11434 or 8000
- [ ] systemd enabled for `ollama` and `ollama-agent`
- [ ] Nginx rate limiting configured
- [ ] [Restic backups](/infrastructure/vps-backup-restore-restic-ubuntu-24-04/) for `/opt/ollama-agent`
- [ ] [Uptime Kuma](/infrastructure/uptime-kuma-monitoring-ubuntu-vps-24-04/) monitoring `/health`

---

## Conclusion

A **self-hosted AI agent on a VPS** with Ollama eliminates per-token API fees and keeps data on your metal — at the cost of slower inference and ops responsibility. Start with `llama3.2:3b` on an 8 GB VPS, wrap with FastAPI, and graduate to [LangChain + cloud APIs](/infrastructure/deploy-langchain-on-vps-ubuntu-24-04/) when you need frontier model quality.

{{< affiliate_box
    name="Vultr"
    url="AFFILIATE_LINK_VULTR"
    cta="Deploy 8 GB VPS"
    badge="Fast NVMe"
    desc="8 GB High Frequency instance — enough RAM for mistral:7b with fast disk for model pulls and logs."
    price="From $24/mo"
>}}

**→ Related:** [Best VPS for AI Agents](/infrastructure/best-vps-for-ai-agents-2026/) · [LangChain deploy](/infrastructure/deploy-langchain-on-vps-ubuntu-24-04/)

*Part of [Phase 1: Infrastructure](/infrastructure/) — [See the full learning path](/start-here/)*
