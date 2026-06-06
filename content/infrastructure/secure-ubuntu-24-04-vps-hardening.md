---
title: "Ubuntu 24.04 VPS Hardening: SSH, UFW & Fail2Ban"
date: 2026-06-05T10:00:00+01:00
lastmod: 2026-06-06T08:00:00+01:00
draft: false
description: "Harden a fresh Ubuntu 24.04 VPS in 30 minutes — non-root sudo user, SSH keys only, UFW firewall, Fail2Ban, and unattended security upgrades before you deploy anything."
keywords:
  - "ubuntu 24.04 server hardening"
  - "secure vps checklist"
  - "ufw fail2ban ubuntu"
  - "ssh hardening ubuntu"
  - "vps security baseline"
  - "unattended upgrades ubuntu"
summary: "A fresh public VPS sees SSH brute-force attempts within minutes. Run this checklist before deploying FastAPI, Hugo, or any agent workload — with verification commands at the end."
series: ["Phase 1: Infrastructure"]
tags: ["ubuntu", "linux", "security", "vps", "ssh", "ufw", "fail2ban", "devops", "infrastructure"]
categories: ["tutorial"]
images: ["/images/og/secure-ubuntu-24-04-vps-hardening.png"]
weight: 1
ShowToc: true
TocOpen: false
faq:
  - q: "How long does Ubuntu 24.04 VPS hardening take?"
    a: "About 30 minutes on a fresh droplet: create a sudo user (5 min), harden SSH (5 min), configure UFW and Fail2Ban (10 min), enable unattended-upgrades and swap (10 min). Always keep a second SSH session open while changing sshd_config so you cannot lock yourself out."
  - q: "Should I change SSH from port 22 to a custom port?"
    a: "For a single VPS with SSH key authentication and Fail2Ban, port 22 is fine — custom ports reduce log noise but break muscle memory and CI deploy keys. If you change the port, update UFW, Fail2Ban jail config, and every GitHub Actions secret that SSHs to the server."
  - q: "What is the minimum firewall setup for a web VPS?"
    a: "UFW default deny incoming, allow outgoing, then explicitly allow OpenSSH (22), HTTP (80), and HTTPS (443). Never expose application ports like 8000 publicly — FastAPI and similar services should listen on 127.0.0.1 behind Nginx."
howto_total_time: "PT30M"
howto_cost: "6"
howto_steps:
  - name: "Create a sudo user with SSH keys"
    text: "Add a deploy user, grant sudo, copy your ed25519 public key to authorized_keys, and verify login in a second terminal before disabling root access."
  - name: "Harden SSH configuration"
    text: "Create /etc/ssh/sshd_config.d/99-hardening.conf with PermitRootLogin no, PasswordAuthentication no, and AllowUsers deploy. Reload ssh and test before closing your root session."
  - name: "Enable UFW default-deny firewall"
    text: "Set default deny incoming, allow OpenSSH plus ports 80 and 443, then enable UFW and confirm Status active."
  - name: "Install and configure Fail2Ban"
    text: "Install fail2ban, create an sshd jail with maxretry 3 and bantime 1h, enable the service, and verify the jail is active."
  - name: "Enable automatic security updates"
    text: "Install unattended-upgrades, run dpkg-reconfigure to enable automatic security patches, and confirm the timer is enabled."
  - name: "Verify the hardening checklist"
    text: "Run sshd -T checks, ufw status, fail2ban-client status, and ss -tulpn to confirm only expected services listen on public interfaces. Reboot and reconnect via SSH."
---

## Overview

Every new Ubuntu 24.04 VPS with a public IPv4 address gets scanned by bots almost immediately. They probe SSH, hunt for default passwords, and look for open management ports. **Hardening is not optional** — it is the step between “I created a droplet” and “I deploy production code.”

This guide is the security baseline for the [QubitLogic infrastructure series](/start-here/). It takes about **30 minutes** on a fresh [Ubuntu 24.04 LTS](https://ubuntu.com/about/release-cycle) server and produces:

- A non-root `sudo` user with SSH key login
- Password and root SSH login disabled
- **UFW** default-deny firewall (SSH, HTTP, HTTPS only)
- **Fail2Ban** banning repeated SSH failures
- **unattended-upgrades** for security patches

When you finish, continue with [VPS provisioning for AI workloads](/infrastructure/how-to-provision-vps-ai-agent-workloads/) or jump straight to [deploying FastAPI](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/).

### At a glance

| Item | Value |
|------|-------|
| Time | ~30 minutes |
| Cost | $6–12/mo VPS (you need a server first) |
| Outcome | SSH keys only, firewall active, auto-patches enabled |
| Next | [Provision VPS](/infrastructure/how-to-provision-vps-ai-agent-workloads/) → [FastAPI deploy](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) |

### Why harden before you deploy

Shodan and credential-stuffing bots scan the entire IPv4 space continuously. Independent scans show a fresh public VPS gets its first SSH probe within **4–15 minutes** of going live — often before you finish installing packages. Deploying FastAPI or Hugo first means you are fixing security while production traffic hits an open attack surface.

### How this guide compares

| | Generic VPS tutorials | This guide |
|---|----------------------|------------|
| Scope | SSH + UFW only | SSH, UFW, Fail2Ban, auto-updates, swap, verification |
| Audience | Any Linux server | **Ubuntu 24.04** developers deploying FastAPI/Hugo next |
| Next step | "Install your app" | Links to [provision](/infrastructure/how-to-provision-vps-ai-agent-workloads/) → [FastAPI](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/) in series order |
| Enterprise | CIS/USG automation (Ubuntu Pro) | Practical baseline without paid subscriptions |

Need CIS Level 1 compliance? Ubuntu Pro's [USG tool](https://ubuntu.com/blog/hardening-automation-for-cis-benchmarks-now-available-for-ubuntu-24-04-lts) automates hundreds of rules. This checklist covers the **critical subset** that stops 95% of automated attacks on a solo-developer VPS.

The checklist below follows the same order we use on every QubitLogic VPS: identity (non-root user), access (SSH keys), network (UFW), intrusion response (Fail2Ban), and maintenance (unattended-upgrades). Application hardening — [Nginx rate limits](/infrastructure/nginx-reverse-proxy-python-ai-api/), [Cloudflare origin locking](/infrastructure/cloudflare-nginx-vps-static-site-api/) — comes after this baseline.

---

## Prerequisites

- A VPS from {{< affiliate_link url="AFFILIATE_LINK_DIGITALOCEAN" >}}DigitalOcean{{< /affiliate_link >}} or {{< affiliate_link url="AFFILIATE_LINK_VULTR" >}}Vultr{{< /affiliate_link >}} running **Ubuntu 24.04** (see [DO vs Vultr benchmark](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/) if you have not picked a provider yet)
- Root or initial `ubuntu` user access via SSH key (password-only images need an extra key-copy step)
- Your laptop’s public key in `~/.ssh/id_ed25519.pub` (generate with `ssh-keygen -t ed25519` if missing)

{{< affiliate_stack >}}

{{< callout type="warning" title="Do this first" >}}
Run this checklist **before** exposing application ports or cloning private repos. If you already deployed services, take a snapshot/backup, then apply these steps during a maintenance window.
{{< /callout >}}

---

## Step 1 — Create a sudo user

Running daily work as `root` means a single mistyped `rm -rf` destroys the entire server. A dedicated `deploy` user with `sudo` limits blast radius while keeping admin access.

Log in as root (or the provider’s default user), then:

```bash
adduser deploy
usermod -aG sudo deploy
```

Copy your SSH public key to the new user (from your laptop):

```bash
ssh-copy-id deploy@YOUR_VPS_IP
```

Or on the server as root:

```bash
install -d -m 700 /home/deploy/.ssh
nano /home/deploy/.ssh/authorized_keys   # paste your .pub line
chown -R deploy:deploy /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

Verify login in a **new terminal** before continuing:

```bash
ssh deploy@YOUR_VPS_IP
```

---

## Step 2 — Harden SSH

Password authentication is the primary vector for VPS compromise. Disabling it and requiring ed25519 keys eliminates dictionary attacks entirely — bots can hammer port 22 forever without getting in.

Use a drop-in file under `sshd_config.d/` rather than editing the main config: Ubuntu package updates will not overwrite your rules.

Edit the SSH daemon config:

```bash
sudo nano /etc/ssh/sshd_config.d/99-hardening.conf
```

Add or confirm these settings:

```ssh
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
LoginGraceTime 30
MaxStartups 3:50:10
AllowUsers deploy
```

`LoginGraceTime 30` closes idle login attempts faster. `MaxStartups 3:50:10` drops excess concurrent unauthenticated connections — useful during SSH floods.

Apply and test in a **second SSH session** (keep the first open until confirmed):

```bash
sudo systemctl reload ssh
```

Official reference: [OpenSSH server hardening](https://infosec.mozilla.org/guidelines/openssh) (Mozilla Infosec).

{{< callout type="info" title="Custom SSH port?" >}}
Moving SSH off port 22 reduces log noise but breaks muscle memory and some CI deploy keys. For a single VPS behind good keys + Fail2Ban, **port 22 is fine**. If you change it, update UFW and every GitHub Actions secret accordingly.
{{< /callout >}}

---

## Step 3 — Configure UFW (default deny)

UFW is a frontend for `iptables`. **Default deny incoming** means every port is closed unless you explicitly allow it — the correct posture for a public VPS. Cloud providers often ship images with no firewall enabled; assume the internet can reach every listening port until you prove otherwise.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw enable
sudo ufw status verbose
```

Expected: `Status: active`, default `deny (incoming)`, rules for 22/80/443.

Docs: [Ubuntu UFW guide](https://help.ubuntu.com/community/UFW).

---

## Step 4 — Install Fail2Ban

SSH keys stop password guessing, but Fail2Ban adds a second layer: repeated failed attempts (misconfigured keys, stale CI deploy keys) trigger an automatic IP ban. On a typical VPS you will see dozens of failed root logins per hour — Fail2Ban keeps that noise from becoming a resource drain.

```bash
sudo apt update
sudo apt install -y fail2ban
```

Create a local jail override:

```bash
sudo tee /etc/fail2ban/jail.d/sshd.local > /dev/null <<'EOF'
[DEFAULT]
banaction = ufw

[sshd]
enabled = true
port = ssh
maxretry = 3
findtime = 10m
bantime = 1h
EOF

sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

Fail2Ban docs: [fail2ban.readthedocs.io](https://fail2ban.readthedocs.io/en/latest/).

---

## Step 5 — Automatic security updates

```bash
sudo apt install -y unattended-upgrades apt-listchanges
sudo dpkg-reconfigure -plow unattended-upgrades   # select Yes
```

Confirm:

```bash
systemctl is-enabled unattended-upgrades
```

Ubuntu reference: [Unattended upgrades](https://wiki.debian.org/UnattendedUpgrades).

---

## Step 6 — Baseline system hygiene

```bash
sudo timedatectl set-timezone Europe/London   # or your TZ
sudo apt update && sudo apt upgrade -y
```

Optional but recommended on 1–2 GB RAM VPS:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf
sudo sysctl -p /etc/sysctl.d/99-swappiness.conf
```

---

## Verification checklist

Run these five commands — all should match the expected output:

| Check | Command | Expected |
|-------|---------|----------|
| Root login off | `sudo sshd -T \| grep permitrootlogin` | `permitrootlogin no` |
| Password auth off | `sudo sshd -T \| grep passwordauthentication` | `passwordauthentication no` |
| Firewall active | `sudo ufw status` | `Status: active` |
| Fail2Ban running | `sudo fail2ban-client status sshd` | `Status for the jail: sshd` |
| Only expected listeners | `sudo ss -tulpn` | `sshd`, later `nginx` — nothing unexpected on `0.0.0.0` |

Reboot test:

```bash
sudo reboot
# wait 30s, then:
ssh deploy@YOUR_VPS_IP
```

---

## Troubleshooting

**Locked out after SSH changes** — Use your provider’s web console (DigitalOcean “Access”, Vultr “View Console”) to fix `sshd_config` or re-enable password auth temporarily.

**UFW blocks your app** — Add the port before enabling: `sudo ufw allow 8000/tcp` (development only; production APIs should sit behind [Nginx on 443](/infrastructure/nginx-reverse-proxy-python-ai-api/)).

**Fail2Ban banned your IP** — `sudo fail2ban-client set sshd unbanip YOUR_IP`.

---

## What this guide does not cover

- Application-level security ([Nginx rate limits, TLS tuning](/infrastructure/nginx-reverse-proxy-python-ai-api/))
- [Cloudflare origin locking](/infrastructure/cloudflare-nginx-vps-static-site-api/)
- Secrets management and [CI/CD deploy keys](/infrastructure/cicd-pipeline-ai-python-scripts/)

Those are the next layers once this baseline is in place.

---

## Frequently Asked Questions

### How long does Ubuntu 24.04 VPS hardening take?

About 30 minutes on a fresh droplet: create a sudo user (5 min), harden SSH (5 min), configure UFW and Fail2Ban (10 min), enable unattended-upgrades and swap (10 min). Always keep a second SSH session open while changing `sshd_config`.

### Should I change SSH from port 22 to a custom port?

For a single VPS with SSH key authentication and Fail2Ban, port 22 is fine. Custom ports reduce log noise but break muscle memory and CI deploy keys. If you change it, update UFW, Fail2Ban jail config, and every GitHub Actions secret that SSHs to the server.

### What is the minimum firewall setup for a web VPS?

UFW default deny incoming, allow outgoing, then explicitly allow OpenSSH (22), HTTP (80), and HTTPS (443). Never expose application ports like 8000 publicly — FastAPI should listen on `127.0.0.1` behind Nginx.

---

## Next steps

1. [Provision a VPS for AI agent workloads](/infrastructure/how-to-provision-vps-ai-agent-workloads/) — benchmarks and Python stack
2. [Deploy FastAPI with Nginx and systemd](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/)
3. [DigitalOcean vs Vultr vs Hetzner benchmark](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/) — pick a provider with data

---

*Affiliate links may appear in partner boxes on this site. See [Affiliate Disclosure](/affiliate-disclosure/).*
