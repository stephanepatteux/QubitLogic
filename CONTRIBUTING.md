# Contributing to QubitLogic

QubitLogic is a personal technical blog. Direct contributions to articles are not accepted, but there are several useful ways to engage.

---

## Reporting errors

If you spot a factual error, outdated command, or broken code example, open an [issue](https://github.com/stephanepatteux/QubitLogic/issues) with:

- The article URL
- The specific claim or code block that is wrong
- What it should say (with a source if possible)

Benchmark corrections are especially welcome — if you run the commands and get materially different numbers, open an issue with your hardware specs and output.

---

## Article context

Each article in the repo corresponds to a live post on [qubitlogic.dev](https://qubitlogic.dev). The series structure:

| Section | Path | Live URL |
|---|---|---|
| Infrastructure | `content/infrastructure/` | [qubitlogic.dev/infrastructure/](https://qubitlogic.dev/infrastructure/) |
| Quantum Coding | `content/quantum-coding/` | [qubitlogic.dev/quantum-coding/](https://qubitlogic.dev/quantum-coding/) |
| Professional Edge | `content/professional-edge/` | [qubitlogic.dev/professional-edge/](https://qubitlogic.dev/professional-edge/) |

Key articles referenced in discussions:

- [How to Provision a VPS for AI Agent Workloads](https://qubitlogic.dev/infrastructure/how-to-provision-vps-ai-agent-workloads/)
- [DigitalOcean vs Vultr vs Hetzner Benchmark 2026](https://qubitlogic.dev/infrastructure/digitalocean-vs-vultr-hetzner-vps-benchmark-2026/)
- [Grover's Search Algorithm in Python](https://qubitlogic.dev/quantum-coding/grovers-search-logic-python/)
- [QAOA vs Classical Brute Force Benchmark](https://qubitlogic.dev/quantum-coding/qaoa-vs-classical-brute-force-benchmarking/)
- [Qiskit vs PennyLane 2026](https://qubitlogic.dev/quantum-coding/qiskit-vs-pennylane-2026/)
- [Qiskit 2.x Migration Guide](https://qubitlogic.dev/quantum-coding/qiskit-2-migration-guide/)
- [Post-Quantum Cryptography for API Security](https://qubitlogic.dev/professional-edge/post-quantum-cryptography-api-security/)
- [Auditing Code for PQC Compliance](https://qubitlogic.dev/professional-edge/auditing-code-post-quantum-compliance/)

---

## Running the site locally

```bash
git clone --recurse-submodules https://github.com/stephanepatteux/QubitLogic.git
cd QubitLogic
bash scripts/setup-dev.sh   # submodules, Hugo Extended, Pillow
hugo server -D
```

If you cloned without `--recurse-submodules`, run `bash scripts/setup-dev.sh` once before starting Hugo.

Requires [Hugo Extended v0.162.1+](https://github.com/gohugoio/hugo/releases).

Open [http://localhost:1313](http://localhost:1313).

---

## Contact

For questions about the content: **hello@qubitlogic.dev**
