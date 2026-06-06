---
title: "Hetzner VPS for Python AI: Provision & Tune Ubuntu 24.04"
date: 2026-06-09T08:00:00+01:00
lastmod: 2026-06-09T08:00:00+01:00
draft: false
description: "Provision a Hetzner Cloud VPS for Python AI workloads on Ubuntu 24.04 — choose CX22 or CX32, apply a Hetzner firewall, install the QubitLogic Python stack, add swap, and verify the box before deploying FastAPI."
keywords:
  - "hetzner ubuntu 24.04 python ai"
  - "hetzner cx22 cx32 setup"
  - "hetzner cloud firewall tutorial"
  - "ubuntu 24.04 fastapi vps"
  - "python ai vps provisioning"
  - "hetzner eu datacenter"
summary: "Hetzner gives European builders unusually strong price-to-RAM value, but most VPS tutorials assume DigitalOcean. This guide adapts the QubitLogic Ubuntu 24.04 Python stack to Hetzner Cloud with the right plan, firewall, swap, and verification steps."
series: ["Phase 1: Infrastructure"]
tags: ["hetzner", "ubuntu", "python", "fastapi", "vps", "ai-agents", "devops", "linux", "infrastructure"]
categories: ["tutorial"]
images: ["/images/og/hetzner-vps-provision-python-ai-ubuntu-24-04.png"]
weight: 14
ShowToc: true
TocOpen: false
faq:
  - q: "Should I choose Hetzner CX22 or CX32 for Python AI workloads?"
    a: "Choose CX22 for a Hugo site plus one small FastAPI app, light background jobs, and modest cron-style agent work. Choose CX32 when you expect multiple workers, heavier pandas jobs, or want more headroom for Docker, Nginx, and queue consumers on the same host. The upgrade path is straightforward, but starting on CX32 avoids memory pressure if your app loads larger Python dependencies."
  - q: "Which Hetzner datacentre should I use?"
    a: "For most European users, pick the closest EU location: Nuremberg (nbg1), Falkenstein (fsn1), or Helsinki (hel1). Lower latency helps both SSH responsiveness and API round-trips. If your traffic and upstream APIs are mostly in Europe, an EU region is the sensible default."
  - q: "Do I still need UFW if Hetzner Cloud Firewall is enabled?"
    a: "Yes. Hetzner Cloud Firewall filters traffic before it reaches the VM, while UFW protects the guest OS itself. Use both: allow only 22, 80, and 443 in the cloud firewall, then keep UFW default-deny on the server. Defence in depth matters on a public VPS."
  - q: "Can I use the same Python stack as the general provisioning guide?"
    a: "Yes. This article uses the same Ubuntu 24.04 package list and Python 3.12 virtual environment pattern as the main provisioning guide: build-essential, Git, curl, tmux, python3.12, python3.12-venv, python3-pip, then FastAPI, Uvicorn, LangChain, HTTPX, Pydantic, and python-dotenv inside a venv."
  - q: "Is Hetzner good for FastAPI and Hugo on one VPS?"
    a: "Yes. A CX22 is enough for a low-traffic Hugo site, Nginx, and a small FastAPI API bound to 127.0.0.1. A CX32 is the safer choice once you add background workers, newsletter jobs, or heavier Python dependencies. Follow the hardening guide first, then the FastAPI deployment guide for production process management and TLS."
howto_total_time: "PT45M"
howto_cost: "5"
howto_steps:
  - name: "Pick a Hetzner Cloud plan and EU region"
    text: "Choose CX22 for a lean stack or CX32 for more RAM and workers, then select the nearest EU datacentre such as nbg1, fsn1, or hel1."
  - name: "Create the server with SSH keys and a cloud firewall"
    text: "Provision Ubuntu 24.04 with your ed25519 key and attach a Hetzner Cloud Firewall allowing only SSH, HTTP, and HTTPS."
  - name: "Update Ubuntu and install the baseline toolchain"
    text: "Apply package upgrades and install the same core Ubuntu 24.04 packages used in the general QubitLogic provisioning guide."
  - name: "Create a Python 3.12 virtual environment"
    text: "Build a project directory under /opt, create a venv, and install the shared FastAPI and AI tooling stack."
  - name: "Tune memory with swap and low-swappiness defaults"
    text: "Add a swapfile and sysctl settings so small CX instances survive bursty Python memory usage without constant swapping."
  - name: "Verify the host before deployment"
    text: "Check CPU, RAM, disk, firewall state, listening ports, and your sample FastAPI health endpoint before moving on to the production deployment guide."
---

## Overview

Most VPS tutorials for Python APIs assume **DigitalOcean first** and only mention Hetzner in passing. That is fine if you need the broadest beginner ecosystem, but it leaves money on the table for European builders. Hetzner Cloud's **CX22** and **CX32** plans are often the better fit for a lean Python AI stack: more RAM per pound or euro, solid AMD-backed virtual cores, and EU datacentres close to many QubitLogic readers.

This guide takes the same Ubuntu 24.04 Python stack used in the main [VPS provisioning guide](/infrastructure/how-to-provision-vps-ai-agent-workloads/) and adapts it to **Hetzner Cloud** specifically:

- Pick between **CX22** and **CX32**
- Deploy in an EU datacentre such as **Nuremberg, Falkenstein, or Helsinki**
- Add a **Hetzner Cloud Firewall** in the console before first login
- Install the same **Python 3.12 + FastAPI + AI tooling** stack used elsewhere in the series
- Tune swap so small instances behave sensibly under bursty Python memory load

Start here, then continue with [Ubuntu 24.04 VPS hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/) and [FastAPI deployment with Nginx and systemd](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/). If you are still deciding between providers, read the full [DigitalOcean vs Vultr vs Hetzner benchmark](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/).

### At a glance

| Item | Value |
|------|-------|
| Best plans | Hetzner Cloud `CX22` or `CX32` |
| OS | Ubuntu 24.04 LTS |
| Best regions for this guide | `nbg1`, `fsn1`, `hel1` |
| Stack | Python 3.12, venv, FastAPI, LangChain, HTTPX, Pydantic |
| Public ports | 22, 80, 443 only |
| Next | [Harden Ubuntu](/infrastructure/secure-ubuntu-24-04-vps-hardening/) → [Deploy FastAPI](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) |

### How this guide compares

| Feature | Generic DigitalOcean tutorials | This guide |
|---------|-------------------------------|------------|
| Provider fit | Assumes DO UI and pricing | Built for **Hetzner Cloud** |
| Plan guidance | "Pick any droplet" | **CX22 vs CX32** recommendation |
| Datacentre advice | US-centric | **EU datacentre** guidance |
| Firewall | Usually UFW only | **Hetzner Cloud Firewall + UFW** |
| Python stack | Varies by article | Matches the [main provisioning guide](/infrastructure/how-to-provision-vps-ai-agent-workloads/) |
| Next step | Often stops at package install | Links to [hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/), [benchmark](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/), and [FastAPI deploy](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) |

The point is not that DigitalOcean tutorials are wrong. The point is that **Hetzner-specific decisions matter**: plan size, region, and the provider firewall all change how a small Ubuntu 24.04 VPS behaves in production.

---

## Prerequisites

- A Hetzner Cloud account with permission to create a server and firewall
- Your local public SSH key in `~/.ssh/id_ed25519.pub`
- Basic command-line familiarity with `ssh`, `apt`, and `systemctl`
- A domain or subdomain ready later if you plan to follow the [FastAPI deployment guide](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/)

{{< affiliate_stack >}}

{{< callout type="warning" title="Apply security first" >}}
Provisioning is not the same thing as hardening. As soon as the server is reachable, run the full [Ubuntu 24.04 VPS hardening checklist](/infrastructure/secure-ubuntu-24-04-vps-hardening/) before treating it as production-ready.
{{< /callout >}}

---

## Step 1 — Choose CX22 or CX32 in the right EU region

For a simple Hugo site plus one FastAPI app, **CX22** is the efficient default. If you expect background workers, larger Python dependencies, or multiple services, start on **CX32**.

| Plan | Good for | Why you would pick it |
|------|----------|-----------------------|
| `CX22` | Hugo + FastAPI + light jobs | Lowest-cost sensible entry point |
| `CX32` | Multiple workers, heavier APIs, more headroom | Extra RAM reduces swap pressure |

For region, keep the VM near your users and upstream services. Hetzner's common EU choices are:

- `nbg1` — Nuremberg
- `fsn1` — Falkenstein
- `hel1` — Helsinki

After creating the server in the console, log in and confirm the basics:

```bash
ssh root@YOUR_HETZNER_IP
hostnamectl
uname -r
```

Expected: Ubuntu 24.04 LTS and the current kernel version for the image.

---

## Step 2 — Create the server with SSH keys and a Hetzner Cloud Firewall

In the Hetzner Cloud console:

1. Create a new server with **Ubuntu 24.04**
2. Add your **SSH key**
3. Attach a **Cloud Firewall**
4. Allow only:
   - TCP `22` from your own IP if possible
   - TCP `80` from `0.0.0.0/0` and `::/0`
   - TCP `443` from `0.0.0.0/0` and `::/0`

That firewall blocks unwanted traffic **before** it reaches your VM. It complements, rather than replaces, [UFW in the hardening guide](/infrastructure/secure-ubuntu-24-04-vps-hardening/).

Once the box is up, connect and verify the assigned network:

```bash
ssh root@YOUR_HETZNER_IP
ip -br a
ss -tulpn
```

On a fresh image you should see very little listening publicly besides SSH.

---

## Step 3 — Update Ubuntu and install the baseline toolchain

The package list below intentionally matches the main [provisioning guide](/infrastructure/how-to-provision-vps-ai-agent-workloads/), so your Hetzner box behaves the same way as the DigitalOcean or Vultr examples used elsewhere on QubitLogic.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    build-essential git curl wget unzip \
    htop iotop ncdu tmux \
    python3.12 python3.12-venv python3.12-dev \
    python3-pip
```

Confirm the runtime versions you actually installed:

```bash
python3.12 --version
pip3 --version
free -h
df -h /
```

If you have not yet created a non-root admin user, stop here and run [the hardening guide](/infrastructure/secure-ubuntu-24-04-vps-hardening/). The remaining commands assume a `deploy` sudo user.

---

## Step 4 — Create the Python 3.12 application environment

This is the same venv-first workflow used in the general provisioning guide. Keep the system Python clean; install app dependencies inside a virtual environment only.

```bash
sudo mkdir -p /opt/ai/myapp
sudo chown -R deploy:deploy /opt/ai
cd /opt/ai/myapp

python3.12 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip wheel setuptools
pip install \
    fastapi \
    uvicorn \
    langchain \
    langchain-openai \
    langgraph \
    openai \
    anthropic \
    httpx \
    pydantic \
    python-dotenv
```

Create a minimal health endpoint so you can verify the environment now and reuse it later in the [FastAPI deployment guide](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/):

```bash
tee /opt/ai/myapp/main.py > /dev/null <<'EOF'
from fastapi import FastAPI

app = FastAPI(title="Hetzner AI API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}
EOF
```

Run it locally on the server:

```bash
cd /opt/ai/myapp
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

In a second SSH session:

```bash
curl -fsS http://127.0.0.1:8000/health
```

Expected JSON:

```bash
{"status":"ok"}
```

Stop `uvicorn` with `Ctrl+C` after the check. In production, switch to the [systemd + Nginx deployment pattern](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/).

---

## Step 5 — Tune memory for small CX plans

Small Python APIs are usually fine on Hetzner, but dependency-heavy workloads can spike RAM during installs, cold starts, or pandas transforms. A modest swapfile reduces the risk of abrupt OOM kills.

For `CX22`, 2 GB swap is a reasonable starting point:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.d/99-swappiness.conf
sudo sysctl --system
```

Verify:

```bash
free -h
swapon --show
sysctl vm.swappiness vm.vfs_cache_pressure
```

If you start on `CX32`, you may still want swap, but memory pressure should be noticeably lower.

---

## Step 6 — Verify the host before deploying anything public

Do a short validation pass now. This catches the usual mistakes before you spend time on Nginx, TLS, or CI/CD.

```bash
lscpu | grep -E 'Model name|^CPU\\(s\\)'
free -h
df -h /
sudo ufw status
sudo ss -tulpn
```

If you want a quick CPU sanity check:

```bash
sudo apt install -y sysbench
sysbench cpu --cpu-max-prime=20000 --time=30 --threads=2 run
```

For a fuller provider comparison, use the [Hetzner benchmark article](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/) rather than treating one short sysbench run as gospel.

---

## Verification

Run these checks before moving on to public deployment:

| Check | Command | Expected |
|-------|---------|----------|
| Ubuntu version | `grep PRETTY_NAME /etc/os-release` | `Ubuntu 24.04 LTS` |
| Python 3.12 present | `python3.12 --version` | Python 3.12.x |
| Swap enabled | `swapon --show` | `/swapfile` listed |
| Firewall posture | `sudo ufw status` | `Status: active` after hardening |
| Sample API works | `curl -fsS http://127.0.0.1:8000/health` | `{"status":"ok"}` when uvicorn is running |
| Only expected public listeners | `sudo ss -tulpn` | SSH now; later Nginx on 80/443 |

If any of these fail, fix them now rather than layering more services on top.

---

## Common mistakes

- **Picking `CX22` for a memory-hungry workload** and then blaming Hetzner when pip installs or Gunicorn workers start swapping constantly
- **Skipping the Hetzner Cloud Firewall** because UFW exists; the provider firewall should still drop unwanted traffic upstream
- **Installing Python packages globally** instead of using a venv under `/opt`
- **Binding FastAPI to `0.0.0.0:8000`** during testing and accidentally exposing it publicly
- **Treating one benchmark run as absolute truth** instead of using the full [three-provider benchmark](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/)

---

## Troubleshooting

**SSH works in the console but not from your laptop** — Check the Hetzner Cloud Firewall source IP for port `22`. If you restricted SSH to your office or home IP, your current network may not match.

**`python3.12` is missing** — Run `sudo apt update` first and confirm the box is actually Ubuntu 24.04 with `lsb_release -ds`.

**The server feels slow during `pip install`** — Check `free -h` and `swapon --show`. On a very small plan, adding swap before heavy installs helps.

**`curl http://127.0.0.1:8000/health` fails** — Make sure the venv is activated, `main.py` exists, and `uvicorn` is running in the current shell.

**You can reach port 8000 from the internet** — Stop the app, confirm no process is bound to `0.0.0.0:8000`, and complete the [hardening guide](/infrastructure/secure-ubuntu-24-04-vps-hardening/) before continuing.

---

## Frequently Asked Questions

### Should I choose Hetzner CX22 or CX32 for Python AI workloads?

Choose `CX22` for a Hugo site plus one small FastAPI app, light background jobs, and modest cron-style agent work. Choose `CX32` when you expect multiple workers, heavier pandas jobs, or want more headroom for Docker, Nginx, and queue consumers on the same host. The upgrade path is straightforward, but starting on `CX32` avoids memory pressure if your app loads larger Python dependencies.

### Which Hetzner datacentre should I use?

For most European users, pick the closest EU location: Nuremberg (`nbg1`), Falkenstein (`fsn1`), or Helsinki (`hel1`). Lower latency helps both SSH responsiveness and API round-trips. If your traffic and upstream APIs are mostly in Europe, an EU region is the sensible default.

### Do I still need UFW if Hetzner Cloud Firewall is enabled?

Yes. Hetzner Cloud Firewall filters traffic before it reaches the VM, while UFW protects the guest OS itself. Use both: allow only `22`, `80`, and `443` in the cloud firewall, then keep UFW default-deny on the server. Defence in depth matters on a public VPS.

### Can I use the same Python stack as the general provisioning guide?

Yes. This article uses the same Ubuntu 24.04 package list and Python 3.12 virtual environment pattern as the main provisioning guide: `build-essential`, Git, curl, tmux, `python3.12`, `python3.12-venv`, `python3-pip`, then FastAPI, Uvicorn, LangChain, HTTPX, Pydantic, and `python-dotenv` inside a venv.

### Is Hetzner good for FastAPI and Hugo on one VPS?

Yes. A `CX22` is enough for a low-traffic Hugo site, Nginx, and a small FastAPI API bound to `127.0.0.1`. A `CX32` is the safer choice once you add background workers, newsletter jobs, or heavier Python dependencies. Follow the hardening guide first, then the FastAPI deployment guide for production process management and TLS.

---

## Next steps

1. [Ubuntu 24.04 VPS hardening](/infrastructure/secure-ubuntu-24-04-vps-hardening/) — lock down SSH, UFW, and Fail2Ban
2. [DigitalOcean vs Vultr vs Hetzner benchmark](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/) — compare real provider performance
3. [How to provision a VPS for AI agent workloads](/infrastructure/how-to-provision-vps-ai-agent-workloads/) — same Python stack on the generic provider path
4. [Deploy FastAPI on Ubuntu 24.04](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) — move from local `uvicorn` testing to production Nginx + systemd

---

*Affiliate links may appear in partner boxes on this site. See [Affiliate Disclosure](/affiliate-disclosure/).*
