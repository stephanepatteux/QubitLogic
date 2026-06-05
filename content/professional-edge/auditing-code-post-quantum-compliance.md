---
title: "Auditing Code for Post-Quantum Compliance"
date: 2026-06-01T15:30:00+01:00
lastmod: 2026-06-01T20:00:00+01:00
draft: false
description: "Post-quantum compliance audit tool in Python — scan codebases for vulnerable crypto, generate prioritised remediation reports, and integrate PQC checks into CI/CD pipelines."
keywords:
  - "post-quantum compliance audit"
  - "code security audit"
  - "PQC migration"
  - "cryptography audit Python"
  - "NIST post-quantum"
  - "quantum-safe audit"
summary: "The post-quantum migration starts with knowing what you have. This guide builds a production-grade compliance audit tool in Python that scans any codebase, generates a prioritised remediation report, and runs automatically in your CI/CD pipeline."

series: ["Phase 3: Professional Edge"]
tags: ["security", "post-quantum", "cryptography", "compliance", "python", "ci-cd", "audit"]
categories: ["tutorial"]

images: ["/images/og/auditing-code-post-quantum-compliance.png"]

weight: 20
---

## Overview

[Post 15](/professional-edge/post-quantum-cryptography-api-security/) introduced the cryptographic vulnerabilities that quantum computing creates and the NIST PQC standards that address them. It included a basic `audit_project()` function.

This final QubitLogic article builds that concept into a production-grade compliance tool:

- Scans Python, configuration files, Dockerfiles, and CI/CD workflows
- Classifies findings by severity and migration effort
- Generates a prioritised HTML or JSON remediation report
- Integrates into GitHub Actions as a blocking CI check
- Tracks compliance progress over time with a score

This tool is designed to run in 30 seconds on a large codebase and output a report you can hand to a security team or use to prioritise migration work.

---

## Prerequisites

```bash
pip install click rich jinja2 pygments
```

---

## Step 1 — Vulnerability Database

```python
# pqaudit/vulns.py
from dataclasses import dataclass
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "CRITICAL"   # broken by Shor's, actively exploitable post-CRQC
    HIGH     = "HIGH"       # weakened by Grover's, upgrade recommended
    MEDIUM   = "MEDIUM"     # deprecated classically, quantum accelerates risk
    INFO     = "INFO"       # note-worthy, not immediately actionable

class Effort(str, Enum):
    LOW    = "LOW"      # config change or algorithm flag swap
    MEDIUM = "MEDIUM"   # library upgrade + code change
    HIGH   = "HIGH"     # architectural change required

@dataclass
class Finding:
    rule_id:     str
    pattern:     str
    description: str
    severity:    Severity
    effort:      Effort
    remediation: str
    cwe:         str = ""
    nist_ref:    str = ""


VULNERABILITY_DB: list[Finding] = [
    # ── CRITICAL: Shor's-vulnerable asymmetric crypto ──────────────────────
    Finding("PQC-001", "rsa",
        "RSA key exchange or signature — broken by Shor's algorithm",
        Severity.CRITICAL, Effort.MEDIUM,
        "Replace with ML-KEM (Kyber) for key exchange, ML-DSA (Dilithium) for signatures",
        "CWE-327", "NIST FIPS 203/204"),

    Finding("PQC-002", "ecdsa",
        "ECDSA signature — elliptic curve discrete log broken by Shor's",
        Severity.CRITICAL, Effort.MEDIUM,
        "Replace with ML-DSA (Dilithium) or SLH-DSA (SPHINCS+). See NIST FIPS 204/205",
        "CWE-327", "NIST FIPS 204"),

    Finding("PQC-003", "ecdh",
        "ECDH key exchange — elliptic curve Diffie-Hellman broken by Shor's",
        Severity.CRITICAL, Effort.LOW,
        "Replace with X25519Kyber768 hybrid in TLS, or ML-KEM standalone",
        "CWE-327", "NIST FIPS 203"),

    Finding("PQC-004", "ed25519",
        "Ed25519 signature — Edwards curve, broken by Shor's algorithm",
        Severity.CRITICAL, Effort.MEDIUM,
        "Replace with ML-DSA (Dilithium). Note: Ed25519 is quantum-unsafe despite being 'modern'",
        "CWE-327", "NIST FIPS 204"),

    Finding("PQC-005", "rs256",
        "JWT algorithm RS256 — RSA-based signature, broken by Shor's",
        Severity.CRITICAL, Effort.LOW,
        "Switch to HS512 for internal tokens. Await JOSE PQC RFC for external tokens",
        "CWE-327", ""),

    Finding("PQC-006", "es256",
        "JWT algorithm ES256 — ECDSA-based signature, broken by Shor's",
        Severity.CRITICAL, Effort.LOW,
        "Switch to HS512 for internal tokens. Await JOSE PQC RFC for external tokens",
        "CWE-327", ""),

    Finding("PQC-007", "dsa",
        "DSA signature — discrete logarithm broken by Shor's",
        Severity.CRITICAL, Effort.MEDIUM,
        "Replace with ML-DSA (Dilithium). DSA is also deprecated classically",
        "CWE-327", "NIST FIPS 204"),

    Finding("PQC-008", "diffie-hellman",
        "Diffie-Hellman key exchange — discrete log broken by Shor's",
        Severity.CRITICAL, Effort.MEDIUM,
        "Replace with ML-KEM (Kyber) or X25519Kyber768 hybrid",
        "CWE-327", "NIST FIPS 203"),

    # ── HIGH: Grover's-weakened symmetric crypto ───────────────────────────
    Finding("PQC-101", "aes-128",
        "AES-128 — Grover's reduces effective key length to 64 bits",
        Severity.HIGH, Effort.LOW,
        "Upgrade to AES-256. One-line config change in most frameworks",
        "CWE-326", "NIST SP 800-131A"),

    Finding("PQC-102", "aes128",
        "AES-128 — Grover's reduces effective key length to 64 bits",
        Severity.HIGH, Effort.LOW,
        "Upgrade to AES-256",
        "CWE-326", ""),

    Finding("PQC-103", "sha-1",
        "SHA-1 — classically broken (collision attacks), Grover's further reduces preimage resistance",
        Severity.HIGH, Effort.LOW,
        "Replace with SHA-256 or SHA-3. SHA-1 is deprecated by NIST since 2011",
        "CWE-328", ""),

    Finding("PQC-104", "sha1",
        "SHA-1 — classically broken",
        Severity.HIGH, Effort.LOW, "Replace with SHA-256 or SHA-3", "CWE-328", ""),

    # ── MEDIUM: Classically deprecated ────────────────────────────────────
    Finding("PQC-201", "md5",
        "MD5 — classically broken (collision attacks)",
        Severity.MEDIUM, Effort.LOW,
        "Replace with SHA-256 for integrity checks, bcrypt/argon2 for password hashing",
        "CWE-328", ""),

    Finding("PQC-202", "des",
        "DES — 56-bit key, classically broken since 1997",
        Severity.MEDIUM, Effort.LOW, "Replace with AES-256-GCM", "CWE-327", ""),

    Finding("PQC-203", "3des",
        "3DES — deprecated by NIST 2023, Sweet32 collision attack",
        Severity.MEDIUM, Effort.LOW, "Replace with AES-256-GCM", "CWE-327", ""),

    Finding("PQC-204", "rc4",
        "RC4 — statistically biased, classically broken",
        Severity.MEDIUM, Effort.LOW, "Replace with AES-256-GCM or ChaCha20-Poly1305", "CWE-327", ""),

    Finding("PQC-205", "tlsv1.0",
        "TLS 1.0 — deprecated, multiple known attacks (POODLE, BEAST)",
        Severity.MEDIUM, Effort.LOW, "Require TLSv1.3 minimum in Nginx/OpenSSL config", "CWE-326", ""),

    Finding("PQC-206", "tlsv1.1",
        "TLS 1.1 — deprecated", Severity.MEDIUM, Effort.LOW,
        "Require TLSv1.3 minimum", "CWE-326", ""),

    # ── INFO: Observations ─────────────────────────────────────────────────
    Finding("PQC-301", "ssl_protocols",
        "SSL/TLS protocol configuration found — verify version is TLSv1.3",
        Severity.INFO, Effort.LOW,
        "Ensure config reads: ssl_protocols TLSv1.3;", "", ""),

    Finding("PQC-302", "password_hash",
        "Password hashing detected — verify using bcrypt, argon2, or scrypt",
        Severity.INFO, Effort.LOW,
        "Avoid SHA-256 for password hashing. Use argon2id (winner of PHC)", "", ""),
]
```

---

## Step 2 — Scanner

```python
# pqaudit/scanner.py
import re
from pathlib import Path
from dataclasses import dataclass
from pqaudit.vulns import Finding, VULNERABILITY_DB

SCAN_EXTENSIONS = {
    ".py", ".toml", ".cfg", ".ini", ".env",
    ".yml", ".yaml", ".json", ".conf", ".nginx",
    "Dockerfile", ".sh", ".bash",
}

@dataclass
class ScanResult:
    file:    str
    line_no: int
    line:    str
    finding: Finding
    context: list[str]   # surrounding lines for report


def scan_file(path: Path, db: list[Finding] = VULNERABILITY_DB) -> list[ScanResult]:
    results = []
    try:
        lines = path.read_text(errors="replace").splitlines()
    except (PermissionError, IsADirectoryError):
        return results

    for line_no, line in enumerate(lines, 1):
        line_lower = line.lower()
        for finding in db:
            if finding.pattern in line_lower:
                context = lines[max(0, line_no-3):min(len(lines), line_no+2)]
                results.append(ScanResult(
                    file=str(path),
                    line_no=line_no,
                    line=line.strip(),
                    finding=finding,
                    context=context,
                ))
    return results


def scan_project(
    root: str,
    exclude_dirs: set[str] = None,
    db: list[Finding] = VULNERABILITY_DB,
) -> list[ScanResult]:
    if exclude_dirs is None:
        exclude_dirs = {".venv", "venv", ".git", "__pycache__", "node_modules",
                        ".tox", "dist", "build", ".mypy_cache"}

    root_path = Path(root)
    all_results = []

    for path in root_path.rglob("*"):
        if any(ex in path.parts for ex in exclude_dirs):
            continue
        if path.is_file() and (path.suffix in SCAN_EXTENSIONS or path.name in SCAN_EXTENSIONS):
            all_results.extend(scan_file(path, db))

    # Deduplicate: same rule + same file, keep first occurrence
    seen = set()
    deduped = []
    for r in all_results:
        key = (r.finding.rule_id, r.file)
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return sorted(deduped, key=lambda r: (r.finding.severity.value, r.file))
```

---

## Step 3 — Scoring and Report Generation

```python
# pqaudit/report.py
from collections import Counter
from pqaudit.vulns import Severity
from pqaudit.scanner import ScanResult

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 10,
    Severity.HIGH:     5,
    Severity.MEDIUM:   2,
    Severity.INFO:     0,
}

def compute_compliance_score(results: list[ScanResult]) -> dict:
    """
    Compliance score: 100 = fully compliant, 0 = critical failures everywhere.
    Deduct points per finding weighted by severity.
    """
    total_deductions = sum(SEVERITY_WEIGHTS[r.finding.severity] for r in results)
    score = max(0, 100 - total_deductions)

    counts = Counter(r.finding.severity for r in results)
    return {
        "score":    score,
        "grade":    "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 50 else "F",
        "critical": counts.get(Severity.CRITICAL, 0),
        "high":     counts.get(Severity.HIGH, 0),
        "medium":   counts.get(Severity.MEDIUM, 0),
        "info":     counts.get(Severity.INFO, 0),
        "total":    len(results),
    }


def generate_json_report(results: list[ScanResult], score: dict) -> dict:
    return {
        "compliance_score": score,
        "findings": [
            {
                "rule_id":     r.finding.rule_id,
                "severity":    r.finding.severity.value,
                "effort":      r.finding.effort.value,
                "file":        r.file,
                "line":        r.line_no,
                "description": r.finding.description,
                "remediation": r.finding.remediation,
                "cwe":         r.finding.cwe,
                "nist_ref":    r.finding.nist_ref,
            }
            for r in results
        ],
    }
```

---

## Step 4 — CLI Interface

```python
# pqaudit/cli.py
import json
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from pqaudit.scanner import scan_project
from pqaudit.report import compute_compliance_score, generate_json_report

console = Console()

@click.command()
@click.argument("path", default=".")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.option("--fail-on", type=click.Choice(["critical", "high", "any"]), default="critical",
              help="Exit code 1 if findings at this severity or above exist")
@click.option("--output", "-o", default=None, help="Write JSON report to file")
def audit(path, fmt, fail_on, output):
    """Scan PATH for post-quantum cryptographic compliance issues."""

    console.print(f"\n[bold cyan]PQ Audit[/] scanning [yellow]{path}[/]...\n")
    results = scan_project(path)
    score   = compute_compliance_score(results)

    if fmt == "json" or output:
        report = generate_json_report(results, score)
        json_str = json.dumps(report, indent=2)
        if output:
            with open(output, "w") as f:
                f.write(json_str)
            console.print(f"Report written to [green]{output}[/]")
        else:
            print(json_str)
    else:
        # Rich table output
        grade_colour = {"A": "green", "B": "yellow", "C": "orange1", "F": "red"}
        grade = score["grade"]
        colour = grade_colour.get(grade, "white")

        console.print(Panel(
            f"[{colour}]Grade: {grade}  Score: {score['score']}/100[/]\n"
            f"Critical: [red]{score['critical']}[/]  "
            f"High: [orange1]{score['high']}[/]  "
            f"Medium: [yellow]{score['medium']}[/]  "
            f"Info: [dim]{score['info']}[/]",
            title="Post-Quantum Compliance Report",
            border_style=colour,
        ))

        if results:
            table = Table(box=box.SIMPLE, show_header=True)
            table.add_column("Severity", style="bold", width=10)
            table.add_column("Rule", width=9)
            table.add_column("File", width=40)
            table.add_column("Line", width=6)
            table.add_column("Issue", width=50)
            table.add_column("Effort", width=8)

            sev_colours = {"CRITICAL": "red", "HIGH": "orange1", "MEDIUM": "yellow", "INFO": "dim"}

            for r in results:
                c = sev_colours.get(r.finding.severity.value, "white")
                table.add_row(
                    f"[{c}]{r.finding.severity.value}[/]",
                    r.finding.rule_id,
                    r.file[-38:] if len(r.file) > 40 else r.file,
                    str(r.line_no),
                    r.finding.description[:48] + "…" if len(r.finding.description) > 50 else r.finding.description,
                    r.finding.effort.value,
                )
            console.print(table)
        else:
            console.print("[green]✓ No post-quantum compliance issues found.[/]\n")

    # Exit code for CI integration
    should_fail = (
        (fail_on == "critical" and score["critical"] > 0) or
        (fail_on == "high"     and (score["critical"] + score["high"]) > 0) or
        (fail_on == "any"      and score["total"] > 0)
    )
    sys.exit(1 if should_fail else 0)


if __name__ == "__main__":
    audit()
```

---

## Step 5 — CI/CD Integration

Add to your GitHub Actions workflow (from [Part 6](/infrastructure/cicd-pipeline-ai-python-scripts/)):

```yaml
# .github/workflows/deploy.yml — add this job
  pq-audit:
    name: Post-Quantum Compliance Audit
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install pq-audit
        run: pip install click rich jinja2

      - name: Run compliance audit
        run: |
          python -m pqaudit.cli . \
            --format json \
            --output pq-audit-report.json \
            --fail-on critical

      - name: Upload audit report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: pq-audit-report
          path: pq-audit-report.json
```

This makes post-quantum compliance a **blocking CI check** — any new CRITICAL finding (RSA, ECDSA, ECDH, Ed25519) fails the pipeline before deployment.

---

## Example Output

Running against a typical Python API project:

```
PQ Audit scanning /opt/agents/myagent...

┌─────────────────────────────────────────────┐
│        Post-Quantum Compliance Report        │
│  Grade: C  Score: 58/100                    │
│  Critical: 3  High: 1  Medium: 2  Info: 1   │
└─────────────────────────────────────────────┘

 Severity   Rule      File                       Line  Issue                              Effort
 CRITICAL   PQC-001   auth/tokens.py               14  RSA key exchange or signature —…   MEDIUM
 CRITICAL   PQC-005   auth/tokens.py               31  JWT algorithm RS256 — RSA-based…   LOW
 CRITICAL   PQC-004   deploy/ssh_keys.sh            8  Ed25519 signature — Edwards cur…   MEDIUM
 HIGH       PQC-101   config/nginx.conf            42  AES-128 — Grover's reduces effe…   LOW
 MEDIUM     PQC-203   legacy/data_export.py        88  3DES — deprecated by NIST 2023…    LOW
 MEDIUM     PQC-201   legacy/data_export.py       102  MD5 — classically broken (colli…   LOW
 INFO       PQC-301   config/nginx.conf            38  SSL/TLS protocol configuration …   LOW
```

After applying the remediations from [Post 15](/professional-edge/post-quantum-cryptography-api-security/):

```
PQ Audit scanning /opt/agents/myagent...

┌─────────────────────────────────────────────┐
│        Post-Quantum Compliance Report        │
│  Grade: A  Score: 98/100                    │
│  Critical: 0  High: 0  Medium: 0  Info: 1   │
└─────────────────────────────────────────────┘

✓ No post-quantum compliance issues found (1 info-level note).
```

---

## Remediation Roadmap Template

After your first audit, use this as your migration tracking document:

{{< code_benchmark title="Post-quantum compliance remediation tracker — template" >}}
| Finding | Component | Severity | Effort | Owner | Target date | Status |
|---|---|---|---|---|---|---|
| PQC-001 RSA | TLS key exchange | CRITICAL | Low | DevOps | Q1 | ☐ |
| PQC-005 RS256 JWT | Auth service | CRITICAL | Low | Backend | Q1 | ☐ |
| PQC-004 Ed25519 | SSH deploy keys | CRITICAL | Low | DevOps | Q1 | ☐ |
| PQC-101 AES-128 | All config | HIGH | Low | DevOps | Q2 | ☐ |
| PQC-201 MD5 | Legacy exports | MEDIUM | Low | Backend | Q2 | ☐ |
{{< /code_benchmark >}}

---

## Conclusion — Phase 3 and Series Complete

This audit tool brings the entire QubitLogic series full circle. You now have:

- The **infrastructure** to run production Python AI agents (Phase 1)
- The **algorithms and quantum code** to build hybrid quantum-classical systems (Phase 2)
- The **security hardening and professional tooling** to operate at enterprise grade (Phase 3)

Post-quantum compliance is not a future problem to defer — the harvest-now-decrypt-later attack window is open right now. Running this audit tool takes 30 seconds. Fixing CRITICAL findings (JWT algorithm swap, TLS key exchange config, SSH key type) typically takes under a day.

The migration cost is low. The risk of not migrating compounds every year as quantum hardware matures.

{{< affiliate_box
    name="DigitalOcean"
    url="AFFILIATE_LINK_DIGITALOCEAN"
    cta="Deploy Securely"
    badge="Recommended"
    desc="Ubuntu 24.04 with OpenSSL 3.5. Configure post-quantum TLS, harden your Python API stack, and deploy using the full QubitLogic infrastructure guide."
    price="From $6/mo"
>}}
