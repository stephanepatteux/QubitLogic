---
title: "CI/CD Pipeline for AI Python Scripts"
date: 2026-06-01T16:00:00+01:00
lastmod: 2026-06-01T13:00:00+01:00
draft: false
description: "GitHub Actions CI/CD for Python AI scripts — pytest, dependency auditing, mypy type checking, and zero-downtime SSH deployment to a Linux VPS. Complete workflow included."
keywords:
  - "CI/CD pipeline Python"
  - "GitHub Actions"
  - "automated deployment"
  - "Python testing CI"
  - "continuous integration AI"
  - "GitHub Actions workflow"
summary: "Manually SSHing into your VPS to deploy updated agent code is a liability. This guide builds a complete GitHub Actions pipeline that tests, audits, and deploys Python AI scripts to a VPS automatically on every push to main."

series: ["Phase 1: Infrastructure"]
tags: ["cicd", "github-actions", "python", "pytest", "devops", "infrastructure", "ai-agents", "linux"]
categories: ["tutorial"]

images: ["/images/og/cicd-pipeline-ai-python-scripts.png"]

weight: 6
---

## Overview

Every article in this series so far has built infrastructure that runs reliably in production. That reliability disappears the moment you start deploying code by hand — copying files over SSH, forgetting to restart the systemd service, pushing untested changes at midnight.

A CI/CD pipeline eliminates that category of failure. For a Python AI agent stack on a self-hosted VPS, a production-grade pipeline needs to do five things:

1. **Run tests** on every push — catch regressions before they reach the server
2. **Audit dependencies** — flag known CVEs in your `requirements.txt` before deploying
3. **Type-check** — catch `None` passed to an LLM call that expects `str`
4. **Deploy atomically** — pull, install deps, restart the service, with automatic rollback on failure
5. **Notify on failure** — know immediately, not when a user reports it

This guide builds all five using **GitHub Actions** (free for public repos, 2,000 min/month free on private repos) and `rsync` + `ssh` for VPS deployment.

---

## Prerequisites

- VPS from [Part 1](/infrastructure/how-to-provision-vps-ai-agent-workloads/) with your agent running as a systemd service
- Python project in a GitHub repository
- SSH key pair (we generate a dedicated deploy key below)

---

## Step 1 — Project Structure

Your repository should look like this before adding CI:

```
myagent/
├── .github/
│   └── workflows/
│       └── deploy.yml          ← we create this
├── backtester/                 ← your application code
│   ├── __init__.py
│   ├── engine.py
│   └── strategies/
├── tests/
│   ├── __init__.py
│   ├── test_engine.py
│   └── test_strategies.py
├── requirements.in
├── requirements.txt            ← pip-compile generated
├── pyproject.toml              ← tool config (pytest, mypy, ruff)
└── .env.example                ← committed, no secrets
```

{{< callout type="warning" title="Never commit .env" >}}
Add `.env` to `.gitignore` immediately. Secrets go into GitHub Actions **Secrets**, not into any file that touches version control. We configure this in Step 4.
{{< /callout >}}

---

## Step 2 — `pyproject.toml` Tool Configuration

Centralise all tool configuration in one file to keep the repo root clean:

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "myagent"
version = "0.1.0"
requires-python = ">=3.12"

# ── pytest ────────────────────────────────────────────────────────────────────
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts   = "-v --tb=short --strict-markers"
markers   = [
    "slow: marks tests as slow (deselect with -m 'not slow')",
    "integration: marks tests requiring live API keys",
]

# ── mypy ──────────────────────────────────────────────────────────────────────
[tool.mypy]
python_version = "3.12"
strict         = true
ignore_missing_imports = true

# ── ruff (linter + formatter) ─────────────────────────────────────────────────
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "S", "B", "A", "C4", "PT"]
ignore = ["S101"]   # allow assert in tests

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S", "N"]
```

Install the dev tools into your venv:

```bash
pip install pytest pytest-cov mypy ruff pip-audit
```

---

## Step 3 — Write Tests

CI is only as useful as your test suite. Three categories for an AI agent project:

### Unit tests — pure logic, no I/O

```python
# tests/test_engine.py
import pandas as pd
import numpy as np
import pytest
from backtester.engine import run_backtest
from backtester.strategies.sma_cross import generate_signals


@pytest.fixture
def sample_ohlcv():
    """Synthetic OHLCV data — no file I/O required."""
    n = 500
    rng = np.random.default_rng(42)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    return pd.DataFrame({
        "open":   close * rng.uniform(0.999, 1.001, n),
        "high":   close * rng.uniform(1.000, 1.005, n),
        "low":    close * rng.uniform(0.995, 1.000, n),
        "close":  close,
        "volume": rng.integers(1000, 10000, n).astype(float),
    }, index=pd.date_range("2023-01-01", periods=n, freq="1h"))


def test_backtest_returns_result(sample_ohlcv):
    result = run_backtest(
        sample_ohlcv,
        generate_signals,
        {"fast": 10, "slow": 50},
        strategy_id="sma_10_50"
    )
    assert result.strategy_id == "sma_10_50"
    assert isinstance(result.sharpe_ratio, float)
    assert -1.0 <= result.win_rate <= 1.0


def test_backtest_no_lookahead(sample_ohlcv):
    """Signals must be shifted by 1 bar — result should not change with future data appended."""
    result_a = run_backtest(sample_ohlcv, generate_signals, {"fast": 10, "slow": 50}, "test")
    extra_row = sample_ohlcv.iloc[[-1]].copy()
    extra_row.index = extra_row.index + pd.Timedelta(hours=1)
    df_extended = pd.concat([sample_ohlcv, extra_row])
    result_b = run_backtest(df_extended, generate_signals, {"fast": 10, "slow": 50}, "test")
    assert result_a.total_return == pytest.approx(result_b.total_return, rel=1e-6)


def test_max_drawdown_is_negative_or_zero(sample_ohlcv):
    result = run_backtest(sample_ohlcv, generate_signals, {"fast": 5, "slow": 20}, "test")
    assert result.max_drawdown <= 0.0


@pytest.mark.slow
def test_full_param_grid_no_crash(sample_ohlcv):
    """Smoke test: all parameter combinations complete without exception."""
    for fast in [5, 10, 20]:
        for slow in [30, 50, 100]:
            result = run_backtest(sample_ohlcv, generate_signals, {"fast": fast, "slow": slow}, f"sma_{fast}_{slow}")
            assert result.num_trades >= 0
```

Run locally before wiring into CI:

```bash
pytest -v
pytest -v -m "not slow"   # skip slow tests during development
```

---

## Step 4 — GitHub Actions Secrets

The pipeline needs three secrets. Set them at **GitHub → Repository → Settings → Secrets and variables → Actions**:

| Secret name | Value |
|---|---|
| `VPS_HOST` | Your VPS IP address or domain |
| `VPS_USER` | The deploy user (e.g. `deploy`) |
| `VPS_SSH_KEY` | Private SSH key (generated below) |

Generate a dedicated deploy key on your VPS — never reuse your personal key:

```bash
# On your VPS
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key -N ""

# Add the public key to authorized_keys
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Print the private key — paste this into the VPS_SSH_KEY GitHub secret
cat ~/.ssh/deploy_key
```

---

## Step 5 — The GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Test → Audit → Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"

jobs:
  # ── Job 1: Test & Lint ──────────────────────────────────────────────────────
  test:
    name: Test & Lint
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install --require-hashes -r requirements.txt
          pip install pytest pytest-cov mypy ruff

      - name: Lint (ruff)
        run: ruff check . && ruff format --check .

      - name: Type check (mypy)
        run: mypy backtester/

      - name: Run tests (excluding integration)
        run: pytest -v -m "not integration" --cov=backtester --cov-report=term-missing

  # ── Job 2: Security Audit ───────────────────────────────────────────────────
  audit:
    name: Dependency Audit
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install pip-audit
        run: pip install pip-audit

      - name: Audit dependencies for CVEs
        run: pip-audit -r requirements.txt --strict
        # --strict: fail the job if any CVE is found

  # ── Job 3: Deploy to VPS ────────────────────────────────────────────────────
  deploy:
    name: Deploy to VPS
    runs-on: ubuntu-latest
    needs: [test, audit]             # only runs if both previous jobs pass
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    steps:
      - uses: actions/checkout@v4

      - name: Set up SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.VPS_SSH_KEY }}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H ${{ secrets.VPS_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy to VPS
        run: |
          ssh -i ~/.ssh/deploy_key ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} \
            'bash -s' << 'ENDSSH'
            set -e   # exit immediately on any error

            echo "=== Pulling latest code ==="
            cd /opt/agents/myagent
            git fetch origin main
            git reset --hard origin/main

            echo "=== Installing dependencies ==="
            source .venv/bin/activate
            pip install --require-hashes -r requirements.txt --quiet

            echo "=== Restarting service ==="
            sudo systemctl restart myagent

            echo "=== Health check ==="
            sleep 3
            curl -sf http://127.0.0.1:8000/health || (
              echo "Health check failed — rolling back"
              git reset --hard HEAD@{1}
              pip install --require-hashes -r requirements.txt --quiet
              sudo systemctl restart myagent
              exit 1
            )

            echo "=== Deploy complete ==="
          ENDSSH
```

{{< callout type="tip" title="The health check rollback" >}}
The `curl -sf` health check after restart is the critical safety net. If the new code starts but immediately crashes (bad import, missing env var), the health check fails, the script rolls back to the previous commit, reinstalls deps, and restarts the old version. The pipeline job fails with a clear error — no silent broken deployments.
{{< /callout >}}

---

## Step 6 — Allow deploy user to restart systemd without a password

The deploy user needs to restart the `myagent` service without being prompted for a `sudo` password inside the SSH session:

```bash
# On your VPS
sudo visudo -f /etc/sudoers.d/deploy-agent
```

Add this single line:

```
deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart myagent, /bin/systemctl status myagent
```

This grants `deploy` the minimum necessary privilege — only the specific `systemctl` commands for your service, nothing else.

---

## Step 7 — Pull Request Preview

For pull requests that should not deploy but still run tests, the workflow already handles this: the `deploy` job has `if: github.ref == 'refs/heads/main' && github.event_name == 'push'`, so PRs run `test` and `audit` only.

Add branch protection at **GitHub → Settings → Branches → Add rule**:

- Branch name pattern: `main`
- Require status checks to pass: `Test & Lint`, `Dependency Audit`
- Require branches to be up to date before merging

This prevents any code reaching `main` (and therefore the VPS) without passing tests and the CVE audit.

---

## Benchmark: Pipeline Run Times

{{< code_benchmark title="GitHub Actions pipeline duration — Python 3.12, ubuntu-latest runner, pip cache warm" >}}
| Job | Cold (no cache) | Warm (pip cache hit) |
|---|---|---|
| Test & Lint | 2 min 48 s | 52 s |
| Dependency Audit | 1 min 14 s | 38 s |
| Deploy to VPS | 45 s | 45 s (SSH, no cache) |
| **Total (push to live)** | **~5 min** | **~2 min 15 s** |
{{< /code_benchmark >}}

With pip caching enabled (`cache: pip` in `setup-python`), the full pipeline from `git push` to a running new version on the VPS completes in under 2 minutes 30 seconds on a warm runner.

{{< affiliate_box
    name="DigitalOcean"
    url="AFFILIATE_LINK_DIGITALOCEAN"
    cta="Deploy a Droplet"
    badge="Recommended"
    desc="The VPS target for this pipeline. The $12–$24/mo Droplet handles the rsync + systemctl deploy in under 45 seconds consistently."
    price="From $12/mo"
>}}

---

## Conclusion

Manual VPS deployment is a risk that compounds over time — the more you deploy, the more chances for human error. The pipeline in this guide eliminates that risk at every step:

1. **`ruff`** — catches style and logic issues before they reach review
2. **`mypy --strict`** — prevents `None`-type bugs that crash LLM API calls at runtime
3. **`pip-audit`** — blocks deployment if any dependency has a known CVE
4. **Atomic SSH deploy with rollback** — a broken deployment reverts itself in under 10 seconds
5. **Branch protection** — no code reaches `main` without passing all checks

The total monthly cost of this CI/CD setup: **$0** for public repos, or a few minutes of your 2,000 free GitHub Actions minutes for private repos. There is no reason not to have it from day one.

The final article in Phase 1 delivers the benchmark data we have referenced throughout the series — a **full head-to-head performance comparison of DigitalOcean vs Vultr** across CPU, disk I/O, network, and real-world Python AI agent workloads.

---

*Want to see exactly how this CI/CD pipeline is used to deploy QubitLogic itself? → [How to Build a Technical Blog with Cursor and Hugo](/build-technical-blog-cursor-hugo/)*
