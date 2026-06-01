---
title: "Post-Quantum Cryptography: API Security Vulnerabilities"
date: 2026-06-01T08:00:00+01:00
lastmod: 2026-06-01T17:30:00+01:00
draft: false
description: "Post-quantum cryptography for Python APIs — which algorithms are vulnerable to quantum attacks, NIST FIPS replacements, and how to audit and migrate your API stack now."
summary: "RSA-2048 and ECDSA are broken by a sufficiently powerful quantum computer. That hardware does not exist yet — but 'harvest now, decrypt later' attacks mean your API traffic is at risk today. Here is what to fix and how."

series: ["Phase 3: Professional Edge"]
tags: ["security", "cryptography", "post-quantum", "api", "python", "tls", "nist"]
categories: ["tutorial"]

images: ["/images/og-default.png"]

faq:
  - q: "Is RSA-2048 still safe to use in 2026?"
    a: "RSA-2048 is safe against classical attacks today. However, 'harvest now, decrypt later' attacks mean adversaries can store encrypted traffic now and decrypt it once fault-tolerant quantum computers exist (estimated 5–15 years). For long-lived secrets and sensitive API traffic, migration to NIST FIPS 203/204/205 algorithms should begin now."
  - q: "Which NIST post-quantum algorithms should I use?"
    a: "NIST finalised three standards in 2024: ML-KEM (FIPS 203) for key encapsulation, ML-DSA (FIPS 204) for digital signatures, and SLH-DSA (FIPS 205) as a hash-based signature fallback. For TLS, migrate to ML-KEM. For code signing, use ML-DSA."
  - q: "How do I find quantum-vulnerable cryptography in my Python codebase?"
    a: "Use static analysis tools to scan for RSA, ECDSA, ECDH, and DH usage. The companion article 'Auditing Code for Post-Quantum Compliance' provides a complete Python scanner that identifies vulnerable primitives and generates a prioritised remediation report."

weight: 15
---

## Overview

In [Post 10](/quantum-coding/grovers-search-logic-python/) we noted that Grover's algorithm halves the effective key length of symmetric ciphers. That is a nuisance — AES-128 becomes AES-64-equivalent, fixable by upgrading to AES-256.

The real threat is asymmetric cryptography. **Shor's algorithm** — a different quantum algorithm — breaks RSA, DSA, and elliptic curve cryptography (ECDH, ECDSA) in polynomial time. Every HTTPS connection, every JWT signed with RS256, every SSH key using ECDSA is vulnerable to a cryptographically relevant quantum computer (CRQC).

We do not have a CRQC today. Best estimates put it 5–15 years away. But there is an attack that works right now, today, with no quantum hardware at all.

---

## The "Harvest Now, Decrypt Later" Threat

Nation-state adversaries are intercepting and storing encrypted TLS traffic today. When a CRQC becomes available, they decrypt it retroactively.

The consequence: any data transmitted under RSA or ECC encryption **today** that must remain confidential for more than 5–10 years is already compromised in a threat model that includes well-resourced adversaries.

Sectors with this exposure:
- Medical records (30-year confidentiality requirement)
- Financial transaction history
- Government communications
- Intellectual property in long patent cycles
- Any API transmitting long-lived secrets or keys

If your API handles data in these categories, the migration timeline starts now.

---

## Which Algorithms Are Broken by Shor's

{{< code_benchmark title="Cryptographic algorithm quantum vulnerability assessment" >}}
| Algorithm | Used for | Quantum attack | Status |
|---|---|---|---|
| RSA-2048 | TLS key exchange, JWT RS256 | Shor's — broken | Replace |
| RSA-4096 | Same | Shor's — broken (harder) | Replace |
| ECDSA P-256 | TLS, JWT ES256, SSH | Shor's — broken | Replace |
| ECDH P-256 | TLS key exchange | Shor's — broken | Replace |
| Ed25519 | SSH, JWT, signing | Shor's — broken | Replace |
| AES-128 | Symmetric encryption | Grover's — weakened | Upgrade to AES-256 |
| AES-256 | Symmetric encryption | Grover's — 128-bit equiv | Keep |
| SHA-256 | Hashing | Grover's — minor impact | Keep (use SHA-384+) |
| SHA-3 | Hashing | Minimal | Keep |
{{< /code_benchmark >}}

{{< callout type="warning" title="Ed25519 is also broken" >}}
Ed25519 is widely praised for its performance and security against classical attacks. It is still vulnerable to Shor's algorithm — the elliptic curve discrete logarithm problem that underpins it is efficiently solvable on a CRQC. Do not mistake "modern" for "quantum-safe."
{{< /callout >}}

---

## NIST PQC Standards (2024)

NIST completed its post-quantum cryptography standardisation process in 2024. Three algorithms were standardised:

| Standard | Algorithm | Use case | Security level |
|---|---|---|---|
| FIPS 203 | ML-KEM (Kyber) | Key encapsulation / key exchange | 128/192/256-bit equiv |
| FIPS 204 | ML-DSA (Dilithium) | Digital signatures | 128/192/256-bit equiv |
| FIPS 205 | SLH-DSA (SPHINCS+) | Digital signatures (hash-based) | 128/192/256-bit equiv |

A fourth algorithm — **FALCON** (FN-DSA) — is being standardised as FIPS 206 for applications where signature size matters.

**In plain English:**
- Replace RSA/ECDH key exchange → **ML-KEM (Kyber)**
- Replace ECDSA/RSA signatures → **ML-DSA (Dilithium)**
- Replace Ed25519 signing → **ML-DSA or SLH-DSA**

---

## Step 1 — Audit Your Python API's Cryptographic Surface

Before migrating anything, map what you are currently using:

```python
# audit/crypto_audit.py
"""
Scan a Python project for cryptographic algorithm usage.
Flags algorithms vulnerable to quantum attacks.
"""
import ast
import sys
from pathlib import Path

VULNERABLE_PATTERNS = {
    # OpenSSL / cryptography library
    "rsa":        "RSA — vulnerable to Shor's algorithm",
    "ec":         "Elliptic curve — vulnerable to Shor's algorithm",
    "ecdsa":      "ECDSA — vulnerable to Shor's algorithm",
    "ecdh":       "ECDH — vulnerable to Shor's algorithm",
    "ed25519":    "Ed25519 — vulnerable to Shor's algorithm",
    "rs256":      "JWT RS256 — RSA signature, vulnerable",
    "es256":      "JWT ES256 — ECDSA signature, vulnerable",
    "ps256":      "JWT PS256 — RSA-PSS signature, vulnerable",
    # Common string literals
    "sha1":       "SHA-1 — classically broken, do not use",
    "md5":        "MD5 — classically broken, do not use",
    "des":        "DES — classically broken, do not use",
    "3des":       "3DES — deprecated",
    "rc4":        "RC4 — classically broken, do not use",
}

SAFE_PATTERNS = {
    "ml-kem": "ML-KEM (Kyber) — NIST FIPS 203",
    "ml-dsa": "ML-DSA (Dilithium) — NIST FIPS 204",
    "slh-dsa": "SLH-DSA (SPHINCS+) — NIST FIPS 205",
    "kyber":  "Kyber — PQC key encapsulation",
    "dilithium": "Dilithium — PQC signatures",
    "aes-256": "AES-256 — quantum-safe symmetric",
    "chacha20": "ChaCha20 — quantum-safe symmetric",
}

def scan_file(path: Path) -> list[dict]:
    findings = []
    text = path.read_text(errors="replace").lower()
    for pattern, description in VULNERABLE_PATTERNS.items():
        if pattern in text:
            lines = [i+1 for i, line in enumerate(path.read_text(errors="replace").split("\n"))
                     if pattern.lower() in line.lower()]
            findings.append({
                "file": str(path),
                "pattern": pattern,
                "description": description,
                "lines": lines,
                "severity": "HIGH",
            })
    return findings


def audit_project(root: str = ".") -> None:
    root_path = Path(root)
    all_findings = []

    for py_file in root_path.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        all_findings.extend(scan_file(py_file))

    if not all_findings:
        print("✓ No vulnerable cryptographic patterns found.")
        return

    print(f"\n{'CRYPTO AUDIT RESULTS':=^60}")
    print(f"Found {len(all_findings)} potential issue(s):\n")
    for f in all_findings:
        print(f"  [{f['severity']}] {f['pattern'].upper()}")
        print(f"         {f['description']}")
        print(f"         File: {f['file']}")
        print(f"         Lines: {f['lines']}\n")

if __name__ == "__main__":
    audit_project(sys.argv[1] if len(sys.argv) > 1 else ".")
```

Run it against your project:

```bash
python -m audit.crypto_audit /opt/agents/myagent
```

---

## Step 2 — Harden TLS Configuration

Your Nginx TLS config from [Part 2](/infrastructure/nginx-reverse-proxy-python-ai-api/) uses TLS 1.3 — that is correct. TLS 1.3 with AES-256-GCM is quantum-safe for the **symmetric** portion of the handshake. The key exchange (currently X25519 ECDH) is not.

**Current state (TLS 1.3, X25519):** vulnerable to harvest-now-decrypt-later  
**Target state (TLS 1.3, X25519Kyber768):** hybrid — safe against both classical and quantum attackers

### Hybrid key exchange in Nginx (2026)

OpenSSL 3.5+ and BoringSSL now support hybrid post-quantum groups. Update your Nginx TLS config:

```nginx
# /etc/nginx/sites-available/myagent — TLS section update
ssl_protocols TLSv1.3;

# Hybrid PQC + classical key exchange groups
# X25519Kyber768Draft00 = X25519 (classical) + Kyber768 (PQC) in one handshake
ssl_ecdh_curve X25519Kyber768Draft00:X25519:P-256;

# Strong cipher suites — AES-256-GCM preferred
ssl_ciphers TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256;
ssl_prefer_server_ciphers off;   # TLS 1.3 clients choose
```

{{< callout type="info" title="Hybrid groups — belt and suspenders" >}}
`X25519Kyber768Draft00` performs both a classical X25519 and a Kyber768 key encapsulation in one handshake. The session key is derived from both. A classical attacker cannot break X25519; a quantum attacker cannot break Kyber768. You are protected against both simultaneously, with minimal overhead (~1ms extra handshake time).
{{< /callout >}}

Check if your OpenSSL supports hybrid groups:

```bash
openssl list -kem-algorithms | grep -i kyber
openssl version
# OpenSSL 3.5.0 — includes ML-KEM/Kyber support
```

---

## Step 3 — Migrate JWT Signatures

Most Python AI APIs use JWT for authentication. The standard `python-jose` and `PyJWT` libraries use RS256 (RSA) or ES256 (ECDSA) by default — both vulnerable.

**Current (vulnerable):**
```python
import jwt
# RS256 — RSA signature, Shor's-vulnerable
token = jwt.encode({"sub": "user123"}, rsa_private_key, algorithm="RS256")
```

**Target (quantum-safe):**

The JWT specification does not yet have a standardised PQC algorithm identifier. The practical interim approach for 2026 is:

1. Migrate to **HS256 or HS512** (HMAC-SHA256/512) for internal service-to-service tokens — symmetric, Grover-resistant with 256-bit keys
2. For external-facing tokens requiring asymmetric verification, track [JOSE PQC draft](https://datatracker.ietf.org/doc/draft-ietf-jose-pqc-kem/) (expected RFC 2026–2027)

```python
# Interim: HS512 for internal tokens
import jwt
import secrets

# Generate a 256-bit secret (store in .env, never hard-code)
SECRET_KEY = secrets.token_hex(32)

token = jwt.encode(
    {"sub": "user123", "exp": ...},
    SECRET_KEY,
    algorithm="HS512"   # HMAC-SHA512 — quantum-safe with 256-bit key
)
```

---

## Step 4 — Python `cryptography` Library: PQC Support

The `cryptography` library (the de facto standard Python crypto library) added ML-KEM support in version 43.0 (released Q4 2024):

```bash
pip install "cryptography>=43.0"
```

```python
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEMPrivateKey, MLKEMPublicKey

# Generate ML-KEM-768 key pair (NIST security level 3 — 192-bit equiv)
private_key = MLKEMPrivateKey.generate(MLKEMPrivateKey.ML_KEM_768)
public_key  = private_key.public_key()

# Encapsulate: sender generates shared secret + ciphertext
ciphertext, shared_secret_sender = public_key.encapsulate()

# Decapsulate: receiver recovers shared secret
shared_secret_receiver = private_key.decapsulate(ciphertext)

assert shared_secret_sender == shared_secret_receiver
print(f"Shared secret (hex): {shared_secret_sender.hex()[:32]}...")
print(f"Ciphertext length:   {len(ciphertext)} bytes")   # 1,088 bytes for ML-KEM-768
```

---

## Migration Priority Matrix

{{< code_benchmark title="API security migration priority — by threat timeline and implementation effort" >}}
| Component | Current algorithm | Replace with | Priority | Effort |
|---|---|---|---|---|
| TLS key exchange | X25519 ECDH | X25519Kyber768 hybrid | High | Low — Nginx config |
| JWT signing (internal) | RS256 / ES256 | HS512 | High | Low — algorithm swap |
| SSH host keys | ECDSA / Ed25519 | RSA-4096 (interim) | Medium | Low |
| SSH client keys | Ed25519 | RSA-4096 (interim) | Medium | Low |
| Code signing | ECDSA | ML-DSA (Dilithium) | Medium | Medium |
| Data-at-rest encryption | AES-128 | AES-256 | High | Low — config change |
| JWT signing (external) | RS256 | Wait for JOSE PQC RFC | Low | — |
| Certificate authority | RSA-2048 | ML-DSA (when CA support arrives) | Low | High |
{{< /code_benchmark >}}

---

## Conclusion

Post-quantum cryptography migration is not a future problem — it is a present operational decision with a 5–15 year planning horizon.

**Act now:**
1. Run `audit_project()` — know what algorithms you are using
2. Switch TLS key exchange to hybrid `X25519Kyber768` — one Nginx config change, zero downtime
3. Migrate AES-128 to AES-256 everywhere — symmetric encryption is cheap to upgrade
4. Switch internal JWT signing to HS512 — a one-line algorithm change

**Plan for:**
- ML-DSA signatures when JOSE PQC RFC stabilises (2026–2027)
- Full certificate chain migration as CA support matures
- Re-keying any long-lived encrypted data stores before CRQC timeline

The final article in this series provides a full **code auditing checklist for post-quantum compliance** — a reproducible tool you can run against any Python codebase.

{{< affiliate_box
    name="DigitalOcean"
    url="AFFILIATE_LINK_DIGITALOCEAN"
    cta="Deploy a Hardened Droplet"
    badge="Recommended"
    desc="Ubuntu 24.04 with OpenSSL 3.5 pre-installed. Configure hybrid PQC TLS in under 10 minutes using the Nginx config from this article."
    price="From $6/mo"
>}}

---

## Further Reading

- [NIST FIPS 203 — ML-KEM (Kyber)](https://csrc.nist.gov/pubs/fips/203/final) — the finalised post-quantum key encapsulation standard your API TLS should migrate to
- [NIST FIPS 204 — ML-DSA (Dilithium)](https://csrc.nist.gov/pubs/fips/204/final) — the finalised post-quantum digital signature standard for JWT and certificate signing
- [NIST FIPS 205 — SLH-DSA (SPHINCS+)](https://csrc.nist.gov/pubs/fips/205/final) — the hash-based signature standard, recommended for long-lived signatures
- [IETF JOSE PQC draft](https://datatracker.ietf.org/doc/draft-ietf-jose-pqc-kem/) — the working draft for post-quantum algorithms in JSON Web Encryption
