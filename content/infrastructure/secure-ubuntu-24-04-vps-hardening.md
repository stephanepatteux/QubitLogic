---
title: "Ubuntu 24.04 VPS Hardening Checklist: SSH, UFW, Fail2Ban, and Auto-Updates"
date: 2026-06-06T10:00:00+01:00
lastmod: 2026-06-06T10:00:00+01:00
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
weight: 7
ShowToc: true
TocOpen: false
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

---

## Prerequisites

- A VPS from [DigitalOcean](https://www.digitalocean.com/pricing) or [Vultr](https://www.vultr.com/pricing/) running **Ubuntu 24.04**
- Root or initial `ubuntu` user access via SSH key (password-only images need an extra key-copy step)
- Your laptop’s public key in `~/.ssh/id_ed25519.pub` (generate with `ssh-keygen -t ed25519` if missing)

{{< affiliate_stack >}}

{{< callout type="warning" title="Do this first" >}}
Run this checklist **before** exposing application ports or cloning private repos. If you already deployed services, take a snapshot/backup, then apply these steps during a maintenance window.
{{< /callout >}}

---

## Step 1 — Create a sudo user

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
AllowUsers deploy
```

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

```bash
sudo apt update
sudo apt install -y fail2ban
```

Create a local jail override:

```bash
sudo tee /etc/fail2ban/jail.d/sshd.local > /dev/null <<'EOF'
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

## Next steps

1. [Provision a VPS for AI agent workloads](/infrastructure/how-to-provision-vps-ai-agent-workloads/) — benchmarks and Python stack
2. [Deploy FastAPI with Nginx and systemd](/infrastructure/deploy-fastapi-ubuntu-24-04-nginx-systemd/)
3. [DigitalOcean vs Vultr vs Hetzner benchmark](/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/) — pick a provider with data

---

*Affiliate links may appear in partner boxes on this site. See [Affiliate Disclosure](/affiliate-disclosure/).*
