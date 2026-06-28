---
# DEV.to — paste front matter when publishing
title: "Self-Hosted AI Agent on a VPS with Ollama + FastAPI (No OpenAI Bill)"
published: false
description: Run Ollama on Ubuntu 24.04 with a FastAPI wrapper, systemd, and Nginx. Local Llama/Mistral inference from $12/mo — no per-token API fees.
tags: ollama, ai, selfhosted, devops
canonical_url: https://qubitlogic.dev/infrastructure/self-hosted-ai-agent-ollama-vps-2026/
cover_image: https://qubitlogic.dev/images/og/self-hosted-ai-agent-ollama-vps-2026.png
---

> **Full setup guide:** [qubitlogic.dev/infrastructure/self-hosted-ai-agent-ollama-vps-2026/](https://qubitlogic.dev/infrastructure/self-hosted-ai-agent-ollama-vps-2026/)

Tired of OpenAI bills for a personal agent? Run **[Ollama](https://ollama.com/)** on a VPS and wrap it with FastAPI + Nginx.

## When self-hosting wins

- Privacy-sensitive prompts (internal docs, unreleased code)
- Predictable **~$12–24/mo** vs spiky API costs
- EU data residency on [Hetzner](https://www.hetzner.com/cloud)

When cloud APIs win: high throughput, frontier models (GPT-4o), sub-second UX at scale.

## RAM requirements (don't skip this)

| Model | RAM |
|:---|:---|
| llama3.2:3b | 4 GB |
| mistral:7b | **8 GB** |
| 13B | 16 GB |

Pick an 8 GB VPS: [best VPS for AI agents](https://qubitlogic.dev/infrastructure/best-vps-for-ai-agents-2026/)

## Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
ollama run llama3.2:3b "Hello from my VPS"
```

Docs: [Ollama Linux install](https://github.com/ollama/ollama/blob/main/docs/linux.md)

## Security — critical

**Never expose port 11434 publicly.** Unauthenticated Ollama instances get mined.

```bash
ss -tlnp | grep 11434
# must show 127.0.0.1:11434 — NOT 0.0.0.0
```

Stack: Ollama on localhost → FastAPI on `127.0.0.1:8000` → Nginx + TLS.

## FastAPI wrapper (sketch)

```python
async with httpx.AsyncClient(timeout=300) as client:
    r = await client.post(
        "http://127.0.0.1:11434/api/generate",
        json={"model": "llama3.2:3b", "prompt": req.prompt, "stream": False},
    )
```

Full `main.py`, systemd units, Nginx config, model sizing table: **[Self-Hosted AI Agent guide](https://qubitlogic.dev/infrastructure/self-hosted-ai-agent-ollama-vps-2026/)**

## CPU vs GPU reality

Expect **4–8 tokens/sec on CPU** for 7B models — fine for batch agents, slow for chat UX. GPU VPS costs more but changes the game.

## Hybrid path

Route simple queries to Ollama, escalate hard ones to OpenAI — see [enterprise RAG architecture](https://qubitlogic.dev/professional-edge/integrating-enterprise-rag-agents/).

---

*Cross-posted from [QubitLogic](https://qubitlogic.dev/) — self-hosted AI infrastructure tutorials.*
