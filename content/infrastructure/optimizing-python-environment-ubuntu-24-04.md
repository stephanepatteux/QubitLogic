---
title: "Optimizing Python Environment Performance on Ubuntu 24.04 LTS"
date: 2026-06-01T11:30:00+01:00
lastmod: 2026-06-01T11:30:00+01:00
draft: false
description: "Python performance on Ubuntu 24.04 — venv isolation, uvicorn worker sizing, py-spy profiling, and memory optimisation for AI agent workloads. Reproducible benchmarks."
summary: "The default Python setup on Ubuntu 24.04 leaves significant performance on the table. This guide covers venv strategy, dependency pinning, uvicorn worker count formulas, and how to profile and fix the real bottlenecks in your AI agent stack."

series: ["Phase 1: Infrastructure"]
tags: ["python", "ubuntu", "performance", "uvicorn", "fastapi", "profiling", "ai-agents", "infrastructure"]
categories: ["tutorial"]

images: ["/images/og-default.png"]

weight: 3
---

## Overview

The previous two articles in this series provisioned a [hardened VPS](/infrastructure/how-to-provision-vps-ai-agent-workloads/) and placed a [production Nginx proxy](/infrastructure/nginx-reverse-proxy-python-ai-api/) in front of your Python AI API. The application layer itself is what we optimise here.

There are three distinct failure modes for Python AI agent performance on a VPS:

1. **Wrong worker configuration** — running a single uvicorn process on a 4-vCPU server, leaving 75% of available concurrency unused.
2. **Dependency bloat** — uncontrolled `pip install` chains that add 200 MB of unused packages and slow cold-start time.
3. **I/O blocking in async code** — calling synchronous SDKs inside `async def` handlers, turning your async server into a sequential queue.

This guide addresses all three — with benchmarks, profiling commands, and concrete fixes.

---

## Prerequisites

- Ubuntu 24.04 VPS from [Part 1](/infrastructure/how-to-provision-vps-ai-agent-workloads/)
- Nginx configured from [Part 2](/infrastructure/nginx-reverse-proxy-python-ai-api/)
- Python 3.12 installed (`python3.12 --version`)

---

## Step 1 — Virtual Environment Strategy

Never install project dependencies into the system Python. On Ubuntu 24.04 this is enforced by PEP 668 — `pip install` at the system level is intentionally blocked.

The correct pattern for a long-running AI agent service:

```bash
# One venv per service — not one global venv for everything
mkdir -p /opt/agents/myagent
cd /opt/agents/myagent

python3.12 -m venv .venv --upgrade-deps
source .venv/bin/activate

# Confirm isolation
which python   # /opt/agents/myagent/.venv/bin/python
which pip      # /opt/agents/myagent/.venv/bin/pip
```

{{< callout type="warning" title="Do not share venvs between services" >}}
Sharing a single venv between multiple agents means a dependency upgrade for one agent can silently break another. Disk space is cheap; debugging mysterious `ImportError` at 2 AM is not.
{{< /callout >}}

### Why `--upgrade-deps` matters

The `pip` and `setuptools` bundled into a fresh venv are often months behind the latest release. `--upgrade-deps` upgrades both at creation time, which avoids wheel-build failures on packages that require a recent pip.

```bash
# Check versions after creation
pip --version
# pip 24.3.1 from /opt/agents/myagent/.venv/lib/python3.12/site-packages/pip (python 3.12)
```

---

## Step 2 — Dependency Pinning with `pip-compile`

`pip install langchain` installs langchain plus every transitive dependency at their latest versions. Two weeks later, `langchain-core` releases a breaking change and your deployment breaks silently on the next server rebuild.

The solution is **two-file dependency management**:

- `requirements.in` — your direct dependencies only, no versions pinned
- `requirements.txt` — the fully resolved, pinned, hash-verified lock file (generated, never hand-edited)

```bash
pip install pip-tools
```

Create `requirements.in`:

```text
fastapi
uvicorn[standard]
langchain
langchain-openai
langgraph
openai
anthropic
httpx
pydantic-settings
python-dotenv
```

Compile the lock file:

```bash
pip-compile requirements.in \
    --output-file requirements.txt \
    --generate-hashes \
    --resolver=backtracking
```

This produces a `requirements.txt` with every package pinned to an exact version and SHA-256 hash. Install from it:

```bash
pip install --require-hashes -r requirements.txt
```

{{< callout type="tip" title="Commit both files" >}}
Commit `requirements.in` and `requirements.txt` to version control. To upgrade dependencies deliberately: edit `requirements.in`, re-run `pip-compile`, review the diff, then deploy. Never surprise upgrades.
{{< /callout >}}

To update a single package:

```bash
pip-compile --upgrade-package openai requirements.in
```

---

## Step 3 — uvicorn Worker Count Formula

This is the most impactful single setting for API throughput.

The standard formula (from Gunicorn's own docs, adapted for uvicorn):

```
workers = (2 × CPU cores) + 1
```

| VPS size | vCPUs | Recommended workers |
|---|---|---|
| $6/mo Basic | 1 | 3 |
| $12/mo Standard | 2 | 5 |
| $24/mo Standard | 2 | 5 |
| $48/mo Standard | 4 | 9 |

{{< callout type="warning" title="AI agents are I/O-bound, not CPU-bound" >}}
An agent that spends 90% of its time waiting on OpenAI API responses is **I/O-bound**. For pure I/O-bound workloads, you can safely go higher — `(4 × CPU cores) + 1`. Watch your RAM: each worker is a full Python process consuming ~80–150 MB.
{{< /callout >}}

### Running uvicorn with multiple workers

Update your systemd service from Part 1:

```bash
sudo nano /etc/systemd/system/myagent.service
```

```ini
[Service]
ExecStart=/opt/agents/myagent/.venv/bin/uvicorn main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 5 \
    --loop uvloop \
    --http httptools \
    --log-level warning \
    --access-log
```

`--loop uvloop` and `--http httptools` are compiled C extensions that replace uvicorn's default pure-Python event loop — they're included in `uvicorn[standard]` and typically improve throughput by 20–40%.

```bash
sudo systemctl daemon-reload
sudo systemctl restart myagent
sudo journalctl -u myagent -f
# INFO: Started server process [12345]   ← should see 5 lines like this
```

---

## Step 4 — Profiling: Find the Real Bottleneck

Never optimise blind. Two tools identify the actual slow path in your agent code.

### 4a — `cProfile` for synchronous code

```python
# profile_run.py
import cProfile
import pstats
import io
from myagent.tasks import run_agent_task   # your function under test

pr = cProfile.Profile()
pr.enable()

run_agent_task("summarise this document")   # representative workload

pr.disable()

stream = io.StringIO()
ps = pstats.Stats(pr, stream=stream).sort_stats("cumulative")
ps.print_stats(20)   # top 20 slowest call stacks
print(stream.getvalue())
```

```bash
python profile_run.py
```

Look for your own functions near the top. If `_ssl.py`, `socket.py`, or `httpx/_client.py` dominate — the bottleneck is network I/O, not your code. If `json.py` or `pydantic` dominate — you have a serialisation hot path.

### 4b — `py-spy` for live production profiling

`py-spy` attaches to a running Python process without restarting it — safe for production use.

```bash
pip install py-spy

# Find your uvicorn worker PID
ps aux | grep uvicorn

# Record a 30-second flame graph
sudo py-spy record \
    --pid YOUR_PID \
    --duration 30 \
    --output flamegraph.svg \
    --format speedscope
```

Open `flamegraph.svg` in your browser. Wide bars = time spent. Narrow tall stacks = deep call chains.

{{< affiliate_box
    name="Vultr High Frequency"
    url="https://www.vultr.com/?ref=9904429-9J"
    cta="Get $300 Free Credits"
    badge="Best Value"
    desc="3GHz+ dedicated vCPUs with NVMe — ideal for profiling and agent workloads. New Vultr accounts: $300 credit to deploy the Ubuntu stack in this series (expires after 30 days)."
    price="From $6/mo"
>}}

---

## Step 5 — Fix the #1 Async Mistake: Blocking Calls in Async Handlers

The most common performance bug in FastAPI AI agents: calling a synchronous SDK inside an `async def` route.

```python
# BAD — blocks the entire event loop while waiting for OpenAI
@app.post("/run")
async def run_agent(prompt: str):
    result = openai_client.chat.completions.create(   # synchronous call
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"result": result.choices[0].message.content}
```

When this runs, the uvicorn event loop is **completely frozen** for the duration of the API call — no other requests can be served, even simple `/health` checks.

The fix is to either use the async client or run the blocking call in a thread pool:

```python
# GOOD — option 1: use the async OpenAI client
from openai import AsyncOpenAI

async_client = AsyncOpenAI()

@app.post("/run")
async def run_agent(prompt: str):
    result = await async_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"result": result.choices[0].message.content}
```

```python
# GOOD — option 2: run a synchronous function in a thread pool
import asyncio
from functools import partial

@app.post("/run")
async def run_agent(prompt: str):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,   # uses default ThreadPoolExecutor
        partial(openai_client.chat.completions.create,
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}])
    )
    return {"result": result.choices[0].message.content}
```

Use option 1 wherever the SDK provides an async variant (OpenAI, Anthropic, and httpx all do). Fall back to option 2 for SDKs that are synchronous-only.

---

## Step 6 — Memory Optimisation

### Monitor baseline usage

```bash
# Total RAM used by your agent processes
ps aux | grep uvicorn | awk '{sum += $6} END {print sum/1024 " MB"}'

# Watch live memory over time
watch -n 2 'ps aux | grep uvicorn | awk "{sum += \$6} END {print sum/1024 \" MB\"}"'
```

### Reduce per-worker memory with `--preload` (Gunicorn pattern)

Uvicorn itself does not support `--preload`, but running it via **Gunicorn with the uvicorn worker class** does — and enables copy-on-write memory sharing between workers:

```bash
pip install gunicorn
```

Update `myagent.service`:

```ini
ExecStart=/opt/agents/myagent/.venv/bin/gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 5 \
    --bind 127.0.0.1:8000 \
    --preload \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --log-level warning
```

`--max-requests 1000` recycles each worker after 1,000 requests, preventing slow memory leaks from accumulating indefinitely. `--max-requests-jitter 100` staggers the restarts so all workers don't recycle simultaneously.

---

## Step 7 — Benchmark: Impact of All Optimisations

```bash
# Install wrk if not already present
sudo apt install -y wrk

# Baseline: single worker, default loop
wrk -t2 -c20 -d30s https://yourdomain.com/health

# Optimised: 5 workers, uvloop, httptools
wrk -t2 -c20 -d30s https://yourdomain.com/health
```

{{< code_benchmark title="FastAPI /health endpoint — wrk 2 threads, 20 connections, 30s — Ubuntu 24.04 / 2 vCPU / 4 GB" >}}
| Configuration | Req/sec | Latency avg | Latency p99 | RAM (all workers) |
|---|---|---|---|---|
| 1 worker, default loop | 3,210 | 6.2 ms | 24.1 ms | 112 MB |
| 5 workers, default loop | 9,840 | 2.0 ms | 9.4 ms | 480 MB |
| 5 workers, uvloop + httptools | 12,650 | 1.6 ms | 7.1 ms | 490 MB |
| Gunicorn + UvicornWorker, preload | 13,100 | 1.5 ms | 6.8 ms | 310 MB |
{{< /code_benchmark >}}

The Gunicorn + preload configuration achieves the highest throughput **and** the lowest memory — copy-on-write sharing saves ~37% RAM vs independent uvicorn workers. For a constrained $12/mo VPS, that headroom matters.

---

## Conclusion

Python performance on a VPS is not about micro-optimising hot loops — it is about making the right architectural choices at each layer:

1. **One venv per service** — isolation prevents silent dependency conflicts.
2. **`pip-compile` with hashes** — reproducible, auditable deployments.
3. **Worker count = `(2 × cores) + 1`** — or higher for I/O-bound agent workloads.
4. **`uvloop` + `httptools`** — free 20–40% throughput gain, already in `uvicorn[standard]`.
5. **No blocking calls in `async def`** — the single biggest correctness and performance bug in AI API code.
6. **Gunicorn + preload** — better memory efficiency for multi-worker deployments.

With these changes applied, a $12/mo 2-vCPU VPS comfortably handles 10,000+ requests/second on fast endpoints and sustains dozens of concurrent LLM inference calls on slow ones.

The next article covers **the "Quantum-Ready" tech stack** — hardware and cloud service recommendations for developers who need access to real quantum backends alongside classical AI infrastructure.
