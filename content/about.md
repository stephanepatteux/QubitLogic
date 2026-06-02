---
title: "About QubitLogic"
date: 2026-06-01T00:00:00+01:00
draft: false
description: "QubitLogic is written by Stephane Patteux — IT Service Manager with 20+ years of infrastructure and operations experience, building systematic trading and AI systems on self-hosted Linux stacks."
hidemeta: true
hideSummary: true
ShowReadingTime: false
ShowBreadCrumbs: false
ShowToc: false
---

## About QubitLogic

QubitLogic is a technical blog covering **quantum computing**, **AI infrastructure**, and **Python development** — with a focus on honest benchmarks, reproducible code, and practical implementation grounded in real systems.

Every benchmark number on this site comes from code actually running in production. Every cloud provider recommendation reflects a decision made with real money at stake.

---

## The Author

QubitLogic is written and maintained by **Stephane Patteux** — a UK-based IT Service Manager with over two decades of infrastructure and operations experience, spanning enterprise environments and self-built production systems.

The content on this site is not theoretical. It is derived directly from designing, building, securing, and operating **Strategy Lab** — a systematic sports trading engine deployed on a custom Linux VPS stack.

**Strategy Lab** is a live, production system that:
- Runs on a hardened Ubuntu 24.04 VPS provisioned exactly as described in [Phase 1](/infrastructure/)
- Executes systematic, mathematically-driven trading logic — not AI-generated signals
- Processes real-time market data via the APIs reviewed in the [Professional Edge](/professional-edge/) series
- Is secured using the post-quantum cryptography and Nginx hardening patterns documented on this site

The VPS benchmarks are not synthetic exercises — they are the evaluations that informed which provider Strategy Lab runs on. The Python environment optimisations are the ones applied to the actual execution stack.

### On the use of AI tooling

AI tools are part of the development workflow. Code generation, documentation drafting, and test scaffolding all benefit from LLM assistance.

The core execution logic of Strategy Lab is purely systematic and mathematically driven. No AI model determines trade entries, exits, or position sizing. The edge is in the mathematical model, not the toolchain.

This distinction matters for the content on QubitLogic: AI is a development accelerator, not a decision-maker. Articles on this site reflect that framing — every benchmark, every architecture recommendation, every code sample is evaluated against whether it works in a real production context, not whether it looks impressive in a demo.

---

## The Series Structure

The site is organised as three linked phases, each building on the last:

| Phase | Section | Focus |
|---|---|---|
| 1 | [Infrastructure](/infrastructure/) | VPS provisioning, Nginx, Python, CI/CD |
| 2 | [Quantum Coding](/quantum-coding/) | Qiskit, QAOA, Grover's, hybrid ML |
| 3 | [Professional Edge](/professional-edge/) | PQC, RAG agents, financial APIs, compliance |

The VPS provisioned in Phase 1 runs the quantum experiments in Phase 2. The security tooling in Phase 3 protects the APIs built throughout. The full learning path is at [/start-here/](/start-here/).

---

## Editorial standards

Benchmark numbers are reproducible — every article includes the exact commands used. Affiliate relationships do not influence verdicts; you will see the same honest recommendation whether or not an affiliate programme exists for that provider. See the [Affiliate Disclosure](/affiliate-disclosure/).

Code for all articles is on [GitHub](https://github.com/stephanepatteux/QubitLogic).

---

## Contact

For collaboration or corrections: **hello@qubitlogic.dev**

For privacy and affiliate enquiries: **privacy@qubitlogic.dev**
