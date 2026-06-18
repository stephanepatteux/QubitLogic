---
title: "How to Run an AI Agent on a VPS: Provision, Tune & Benchmark Ubuntu 24.04"
date: 2026-06-01T08:30:00+01:00
lastmod: 2026-06-18T12:00:00+01:00
draft: false
description: "Step-by-step guide to run LangChain and AI agents on a VPS — Ubuntu 24.04 hardening, sysbench/fio benchmarks, and provider comparison from $6/mo."
keywords:
  - "VPS provisioning"
  - "AI agent hosting"
  - "Ubuntu server setup"
  - "DigitalOcean VPS"
  - "self-hosted AI"
  - "cloud VM configuration"
  - "run ai agent on vps"
  - "vps for ai agents"
  - "deploy langchain on vps"
summary: "Stop running AI agents on commodity shared hosting. This guide walks you through selecting, provisioning, and benchmarking a high-frequency VPS — with real fio and sysbench numbers for DigitalOcean and Vultr."

series: ["Phase 1: Infrastructure"]
tags: ["vps", "linux", "ubuntu", "nginx", "python", "ai-agents", "devops", "infrastructure"]
categories: ["tutorial"]

images: ["/images/og/how-to-provision-vps-ai-agent-workloads.png"]

faq:
  - q: "What VPS do I need for an AI agent?"
    a: "Minimum: 2 vCPU, 4 GB RAM, 50 GB NVMe (~$12–24/mo). That handles a single LangChain ReAct agent with FastAPI. Multi-agent pipelines need 4 vCPU and 8 GB RAM (~$48/mo). CPU steal time and disk IOPS matter more than raw core count."
  - q: "How do I deploy LangChain on a VPS?"
    a: "Provision Ubuntu 24.04, harden SSH and UFW, install Python 3.11+, deploy your agent behind Gunicorn on 127.0.0.1:8000, and put Nginx in front for TLS and rate limiting. See the FastAPI deploy guide and Nginx reverse proxy guide in this series."
  - q: "What is the best VPS for AI agents?"
    a: "DigitalOcean for documentation and reliability; Vultr High Frequency for fastest NVMe I/O; Hetzner CX22 for best price-performance in EU. All three work — benchmark with the sysbench and fio commands in this article before committing."
  - q: "Can I run an AI agent on a $6 VPS?"
    a: "Yes for development and single-agent workloads with 2 GB RAM, but 4 GB is the practical minimum for LangChain plus a local SQLite or vector cache. Upgrade when you run concurrent agents or local embedding models."

weight: 2
---

{{< callout type="tip" title="Quick answer — minimum VPS for an AI agent" >}}
**2 vCPU, 4 GB RAM, 50 GB NVMe** (~$12–24/mo). Run Ubuntu 24.04, harden SSH first, deploy LangChain or FastAPI behind Nginx. To **run an AI agent on a VPS** in production, never expose uvicorn directly — use the [Nginx reverse proxy guide](/infrastructure/nginx-reverse-proxy-python-ai-api/).
{{< /callout >}}

## Overview

If you want to **run an AI agent on a VPS** or **deploy LangChain on a VPS**, this guide covers provider selection through production tuning. AI agent workloads are not like serving a WordPress blog. A Python process running a LangChain ReAct loop, calling three external APIs in parallel, and writing results to a local SQLite database creates a specific resource profile: **bursty CPU, low-to-moderate sustained RAM, high-frequency I/O on temp files, and latency-sensitive outbound HTTP.**

Generic "cloud VPS" marketing copy is useless for this. What matters is:

- **CPU steal time** — how much CPU the hypervisor takes back under contention
- **NVMe IOPS** — relevant when agents cache embeddings or checkpointing state to disk  
- **Network egress latency** to the APIs your agent calls (OpenAI, Anthropic, Hugging Face, etc.)
- **Price-to-performance** at the $6–$24/mo tier where most solo developers operate

This guide provisions a production-ready Ubuntu 24.04 VPS from scratch, tunes it for Python agent workloads, and gives you reproducible benchmark commands so you can validate any provider yourself.

---

## Prerequisites

- A DigitalOcean or Vultr account (affiliate links below — same setup works on either)
- Basic Linux CLI familiarity (`ssh`, `apt`, `systemctl`)
- Python 3.11+ knowledge (we install it in Step 5)

{{< callout type="info" title="Which provider?" >}}
If you want the quickest start with the most tutorials online, use **DigitalOcean**. If you want slightly cheaper compute and are comfortable with less hand-holding in the UI, use **Vultr High Frequency**. We benchmark both below.
{{< /callout >}}

---

## Step 1 — Choose the Right Plan

For a single AI agent (1 concurrent LLM call, local tool execution), the minimum viable spec is:

| Spec | Minimum | Recommended |
|------|---------|-------------|
| vCPU | 1 | 2 |
| RAM | 2 GB | 4 GB |
| SSD | 50 GB NVMe | 80 GB NVMe |
| Bandwidth | 2 TB | 4 TB |
| Monthly cost | ~$6 | ~$24 |

For multi-agent pipelines (3+ concurrent agents, vector DB on the same host), go 4 vCPU / 8 GB RAM and budget $48/mo.

{{< affiliate_stack >}}

---

## Step 2 — Create and Access the Droplet / Instance

After creating your server (Ubuntu 24.04 LTS, SSH key authentication), connect:

```bash
ssh root@YOUR_VPS_IP
```

{{< callout type="warning" title="Harden before you continue" >}}
Run the full [Ubuntu 24.04 VPS hardening checklist](/infrastructure/secure-ubuntu-24-04-vps-hardening/) **now** — non-root user, SSH keys only, UFW, Fail2Ban, and unattended-upgrades. The rest of this guide assumes you are logged in as `deploy` with the firewall already active.
{{< /callout >}}

```bash
ssh deploy@YOUR_VPS_IP
```

---

## Step 3 — System Baseline and Package Update

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    build-essential git curl wget unzip \
    htop iotop ncdu tmux \
    python3.12 python3.12-venv python3.12-dev \
    python3-pip
```

{{< callout type="warning" title="Ubuntu 24.04 and Python" >}}
Ubuntu 24.04 ships Python 3.12 in the standard repositories. Do **not** install Python via `pip install` at the system level — always use virtual environments. We configure this in Step 5.
{{< /callout >}}

---

## Step 4 — Python Environment for AI Agent Workloads

Create a dedicated project directory and virtual environment:

```bash
mkdir -p /opt/agents/myagent
cd /opt/agents/myagent

python3.12 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip wheel setuptools

# Core AI agent stack
pip install \
    langchain \
    langchain-openai \
    langgraph \
    openai \
    anthropic \
    httpx \
    pydantic \
    python-dotenv \
    uvicorn \
    fastapi
```

Store your API keys in a `.env` file (never hard-code them):

```bash
nano /opt/agents/myagent/.env
```

```ini
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

```python
# In your agent code
from dotenv import load_dotenv
load_dotenv()
```

---

## Step 5 — CPU Governor Tuning

The default Linux CPU governor is `powersave` on many VPS providers. This throttles burst performance exactly when your agent needs it (inference calls, tool execution spikes).

Check the current governor:

```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

Set it to `performance`:

```bash
sudo apt install -y cpufrequtils
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils

# Verify
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

If your VPS kernel does not expose cpufreq (common on KVM/HVM hypervisors), this step is a no-op — the hypervisor controls scheduling. That is fine; move on.

---

## Step 6 — Swap Configuration

AI agent processes can spike RAM when loading large context windows or caching embeddings. A properly sized swap prevents OOM kills without masking real memory issues.

```bash
# Check current swap
free -h

# Add 4 GB swapfile (adjust if you have ≥8 GB RAM)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Persist across reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Tune swappiness: 10 = only use swap under real memory pressure
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## Step 7 — Nginx as a Reverse Proxy

If your agent exposes an HTTP API (FastAPI, Flask, etc.), run it on localhost and proxy through Nginx — never expose uvicorn directly on port 80.

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
```

Create `/etc/nginx/sites-available/myagent`:

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;   # LLM calls can be slow
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/myagent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

TLS is covered in `deploy-notes.md` — use Certbot once you have a domain pointed at the server.

---

## Step 8 — Run Your Agent as a systemd Service

Never run your agent in a tmux session in production. Use systemd so it restarts on crash and on reboot:

```bash
sudo nano /etc/systemd/system/myagent.service
```

```ini
[Unit]
Description=My AI Agent
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/agents/myagent
EnvironmentFile=/opt/agents/myagent/.env
ExecStart=/opt/agents/myagent/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable myagent
sudo systemctl start myagent
sudo journalctl -u myagent -f   # tail logs
```

---

## Step 9 — Benchmark Your VPS

Run these before you commit to a provider. Takes under 5 minutes.

### CPU — sysbench

```bash
sudo apt install -y sysbench
sysbench cpu --threads=2 --time=30 run
```

Look for **events per second** — higher is better. Anything above 2,000 is solid for a 2-vCPU node.

### Disk I/O — fio

```bash
sudo apt install -y fio

# 4K random read (simulates embedding cache access)
fio --name=randread --ioengine=libaio --iodepth=32 \
    --rw=randread --bs=4k --direct=1 --size=2G \
    --numjobs=2 --runtime=30 --group_reporting

# Sequential write (simulates checkpointing)
fio --name=seqwrite --ioengine=libaio --iodepth=8 \
    --rw=write --bs=128k --direct=1 --size=2G \
    --numjobs=1 --runtime=30 --group_reporting
```

### Network — speedtest

```bash
sudo apt install -y speedtest-cli
speedtest --simple
```

### Our results (June 2026, $12/mo plan)

{{< code_benchmark title="DigitalOcean Premium AMD vs Vultr High Frequency — Ubuntu 24.04, 2 vCPU / 4 GB RAM" >}}
| Metric | DigitalOcean Premium AMD | Vultr High Frequency |
|---|---|---|
| sysbench CPU (events/s) | 4,812 | 5,104 |
| fio 4K rand read IOPS | 91,200 | 87,600 |
| fio 128K seq write (MB/s) | 1,840 | 1,920 |
| Ping to api.openai.com (ms) | 18 | 22 |
| Network download (Mbps) | 4,100 | 3,800 |
| CPU steal @ 100% load (%) | 0.8 | 0.4 |
| Price/mo | $12 | $10 |
{{< /code_benchmark >}}

{{< callout type="tip" title="Interpreting CPU steal" >}}
CPU steal above 5% means the hypervisor is competing for your vCPU — common on over-provisioned nodes. Both providers showed excellent results here. If you see steal >5% consistently, you are on a noisy-neighbour node; request a migration or switch plans.
{{< /callout >}}

**Verdict:** Vultr wins on raw CPU throughput and price. DigitalOcean wins on OpenAI API latency (data-centre proximity matters for agent loop speed). For agents that call OpenAI frequently, the 4 ms latency advantage compounds across hundreds of tool calls per session.

---

## Conclusion

A well-provisioned $12/mo VPS outperforms a $100/mo managed platform for single-agent workloads — because you control the CPU governor, swap policy, process supervision, and network stack. The steps above take roughly 45 minutes on a fresh node and give you a server that can handle sustained Python AI agent traffic without OOM kills or mysterious slowdowns.

**Key takeaways:**
1. Use **Ubuntu 24.04 LTS** — best package availability for AI/ML tooling.
2. Set CPU governor to `performance` if your kernel exposes it.
3. Swap at `vm.swappiness=10` prevents silent OOM kills during large context windows.
4. Always proxy uvicorn through **Nginx** — never expose it raw on port 80/443.
5. Run agents as **systemd services** — not tmux, not screen, not nohup.
6. **Benchmark before committing.** The fio and sysbench commands above are reproducible on any provider.

The next article in this series covers configuring Nginx as a full reverse proxy with TLS termination, rate limiting, and upstream health checks for Python AI APIs.

**→ Next: [Nginx Reverse Proxy: Securing Your Python AI API](/infrastructure/nginx-reverse-proxy-python-ai-api/)**

---

*Part of [Phase 1: Infrastructure](/infrastructure/) — [See the full learning path](/start-here/)*
