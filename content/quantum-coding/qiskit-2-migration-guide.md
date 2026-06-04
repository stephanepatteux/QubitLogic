---
title: "Qiskit 2.x Migration Guide: Breaking Changes and How to Fix Them"
date: 2026-06-02T10:00:00+01:00
lastmod: 2026-06-02T10:00:00+01:00
draft: false
description: "Qiskit 2.x migration guide — fix QuantumCircuit, Sampler, Estimator, and transpiler breaking changes. Side-by-side old vs new code for every major API shift."
summary: "Qiskit 2.x removed the legacy execute() function, changed the Sampler and Estimator primitives interface, and restructured the transpiler. This guide fixes every common breaking change with side-by-side before/after code."

series: ["Phase 2: Quantum Coding"]
tags: ["qiskit", "migration", "python", "quantum-computing", "qiskit-2", "primitives", "transpiler"]
categories: ["tutorial"]

images: ["/images/og-default.png"]

faq:
  - q: "What are the biggest breaking changes in Qiskit 2.x?"
    a: "The three major breaking changes are: (1) execute() was removed — use Sampler or Estimator primitives instead; (2) the backend.run() interface changed; (3) the transpiler pass manager API was restructured with generate_preset_pass_manager(). Most code written for Qiskit 0.x or 1.x will need updates to these three areas."
  - q: "How do I migrate from execute() to the Sampler primitive?"
    a: "Replace `execute(circuit, backend, shots=1000).result().get_counts()` with `from qiskit_ibm_runtime import SamplerV2; sampler = SamplerV2(backend); job = sampler.run([circuit]); result = job.result()[0].data.meas.get_counts()`. The key change is that results are now accessed via the data attribute on each PubResult."
  - q: "Is Qiskit 2.x backwards compatible with Qiskit 1.x code?"
    a: "Partially. QuantumCircuit, gates, and most circuit construction code is backwards compatible. The major incompatibilities are the execution layer: execute(), backend.run() deprecations, the primitives interface (Sampler/EstimatorV1 vs V2), and transpiler pass manager changes. Most algorithm code in qiskit-algorithms also needs updates."

weight: 15
---

Your Qiskit code is broken. You ran `pip install qiskit --upgrade`, came back to a project you haven't touched in six months, and now everything throws `ImportError` or `DeprecationWarning`. The `execute()` function is gone. `SamplerV1` complaints are everywhere. The transpiler API looks different.

This is not a subtle change. Qiskit 2.x completed a migration that started in Qiskit 1.x — moving from the old imperative execution model to a clean, hardware-agnostic primitives model. The old APIs weren't just deprecated; they were removed.

This guide fixes each breaking change directly, with side-by-side before/after code. Work through the sections that match your errors and you will have working code by the end.

---

## What Changed and Why

To understand the fixes, you need a one-paragraph mental model of what Qiskit actually did.

In Qiskit 0.x, you ran circuits by calling `execute(circuit, backend, shots=1000)`. This was convenient but tightly coupled — the execution model, the result format, and the backend API were all baked together. When IBM introduced real quantum hardware with noise and hardware-specific gate sets, this monolithic approach created a mess: different backends returned results in subtly different formats, transpilation was often implicit and surprising, and writing code that worked identically on a simulator and on real hardware required defensive workarounds.

Qiskit 1.x introduced **primitives** as a cleaner abstraction. A `Sampler` primitive runs circuits and returns quasi-probability distributions (what you get from measuring qubits). An `Estimator` primitive computes expectation values of observables without full state vector sampling. Both primitives expose the same interface whether the backend is a local simulator, a noisy simulator, or a real IBM quantum device. Your algorithm code stays the same; only the backend passed to the primitive changes.

Qiskit 2.x completed that transition. The legacy `execute()` function and `backend.run()` are **gone**. `SamplerV1` and `EstimatorV1` are gone. If your code imports either, it will not run.

The benefit: code you write today against the primitives interface will run unchanged on the 127-qubit Eagle processor, the Heron generation hardware, or any future IBM backend. The short-term pain of migration is real, but the resulting code is cleaner and more portable.

The official [Qiskit 2.0 Migration Guide](https://docs.quantum.ibm.com/migration-guides/qiskit-2.0) covers the full picture. This article focuses on the six most common code patterns that break.

---

## Quick Diagnosis — Are You Affected?

Scan your project for these patterns before diving into fixes. If you see any of them, that file needs updating.

**Broken imports and patterns:**

```python
# BROKEN in Qiskit 2.x
from qiskit import execute                        # ImportError
from qiskit.primitives import Sampler             # SamplerV1 — removed
from qiskit.primitives import Estimator           # EstimatorV1 — removed
from qiskit_ibm_runtime import SamplerV1          # removed
from qiskit_ibm_runtime import EstimatorV1        # removed
result = backend.run(circuit).result()            # deprecated / broken
counts = execute(qc, backend, shots=1024).result().get_counts()
```

**Exact errors you'll see:**

```
ImportError: cannot import name 'execute' from 'qiskit'
```

```
ImportError: cannot import name 'SamplerV1' from 'qiskit_ibm_runtime'
```

```
DeprecationWarning: The method ``qiskit.execute_function.execute`` is
deprecated as of qiskit 0.46.0. It will be removed in Qiskit 1.0. Use
Sampler primitive instead.
```

```
AttributeError: 'SamplerPubResult' object has no attribute 'quasi_dists'
```

That last one is subtle — it hits people who migrated to `SamplerV2` but are still reading results using the V1 format.

If your code is clean of all the above patterns, you are likely already compatible. If not, pick up at the relevant fix below.

---

## Fix 1: Replacing execute() with SamplerV2

This is the most common break. The `execute()` function was the go-to way to run a circuit and get measurement counts. It is gone. The replacement is `SamplerV2`.

**Before (Qiskit 0.x / 1.x):**

```python
from qiskit import QuantumCircuit, execute
from qiskit_aer import AerSimulator

backend = AerSimulator()

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

job = execute(qc, backend, shots=1024)
result = job.result()
counts = result.get_counts(qc)
print(counts)  # {'00': 512, '11': 512}
```

**After (Qiskit 2.x):**

```python
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.primitives import StatevectorSampler  # local, no backend needed
# OR for Aer:
from qiskit_aer.primitives import SamplerV2

backend = AerSimulator()

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

sampler = SamplerV2(backend)
job = sampler.run([qc], shots=1024)  # pass a list of circuits
result = job.result()

# Results are now accessed via PubResult objects
pub_result = result[0]                          # first circuit's result
counts = pub_result.data.meas.get_counts()      # .data.<register_name>.get_counts()
print(counts)  # {'00': 512, '11': 512}
```

**Three things to notice in the new pattern:**

1. `sampler.run()` takes a **list** of circuits, not a single circuit. Even if you have one circuit, wrap it: `[qc]`.
2. `job.result()` returns a list of `PubResult` objects, indexed by position in the input list. `result[0]` is the result for `qc`.
3. Counts are accessed as `pub_result.data.<register_name>.get_counts()`. The register name defaults to `meas` if you used `qc.measure_all()` or named your classical register `meas`. If you used a custom register name like `cr`, it would be `pub_result.data.cr.get_counts()`.

The [Grover's search implementation](/quantum-coding/grovers-search-logic-python/) on this site uses the updated Qiskit 2.x SamplerV2 pattern throughout — refer to it for a full working example of this approach in context.

See the full [Qiskit primitives documentation](https://docs.quantum.ibm.com/guides/primitives) for the complete `SamplerV2` API reference.

---

## Fix 2: Replacing execute() with EstimatorV2

If you were using `execute()` to compute expectation values — common in variational algorithms like VQE — the replacement is `EstimatorV2`. The key concept to understand first is the **PUB (Primitive Unified Bloc)**: a tuple of `(circuit, observables, parameter_values)` that you pass to the Estimator.

**Before (Qiskit 0.x / 1.x):**

```python
from qiskit import QuantumCircuit, execute
from qiskit.opflow import Z, StateFn, PauliSumOp
from qiskit_aer import AerSimulator

# Old pattern: construct operator, use execute with statevector, extract manually
backend = AerSimulator(method='statevector')
qc = QuantumCircuit(1)
qc.h(0)

job = execute(qc, backend)
state = job.result().get_statevector()
# ... manual expectation value calculation
```

**After (Qiskit 2.x):**

```python
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives import StatevectorEstimator  # local, exact
# OR for Aer:
from qiskit_aer.primitives import EstimatorV2

qc = QuantumCircuit(1)
qc.h(0)

# Define the observable as a SparsePauliOp
observable = SparsePauliOp("Z")  # measure expectation of Pauli Z

estimator = StatevectorEstimator()

# Build a PUB: (circuit, observable)
# For parameterized circuits, it's (circuit, observable, parameter_values)
pub = (qc, observable)

job = estimator.run([pub])  # pass list of PUBs
result = job.result()

pub_result = result[0]
expectation_value = pub_result.data.evs   # expectation values array
std_dev = pub_result.data.stds            # standard deviations
print(f"<Z> = {expectation_value}")       # ~0.0 for |+> state
```

**For parameterized circuits (VQE-style):**

```python
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives import StatevectorEstimator
import numpy as np

theta = ParameterVector("θ", 2)
qc = QuantumCircuit(2)
qc.ry(theta[0], 0)
qc.ry(theta[1], 1)
qc.cx(0, 1)

observable = SparsePauliOp.from_list([("ZZ", 1.0), ("XX", 0.5)])
parameter_values = np.array([0.3, 0.7])

estimator = StatevectorEstimator()
pub = (qc, observable, parameter_values)   # three-tuple PUB

job = estimator.run([pub])
evs = job.result()[0].data.evs
print(f"Expectation value: {evs}")
```

This pattern feeds directly into the QAOA implementation — see the [quantum-inspired optimizer article](/quantum-coding/quantum-inspired-optimizer-python/) for a full worked example that uses `EstimatorV2` with a parameterized cost Hamiltonian.

{{< callout type="tip" title="Confused by the primitives model?" >}}
Free [IBM Quantum Learning](https://learning.quantum.ibm.com/) covers measurement and execution basics. See the [Quantum Developer Toolkit](/quantum-developer-toolkit/) for courses and tools we use.
{{< /callout >}}

---

## Fix 3: Transpiler Pass Manager

The old `transpile()` function still exists in Qiskit 2.x but should be replaced with the explicit pass manager pattern. The reason: `transpile()` with default arguments can produce poor results — the new API makes optimization decisions explicit and reproducible.

**Before:**

```python
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

backend = AerSimulator()
qc = QuantumCircuit(3)
qc.h(0)
qc.cx(0, 1)
qc.cx(1, 2)

# Old: transpile implicitly, run directly
transpiled = transpile(qc, backend, optimization_level=2)
job = backend.run(transpiled, shots=1024)
counts = job.result().get_counts()
```

**After:**

```python
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2

backend = AerSimulator()
qc = QuantumCircuit(3, 3)
qc.h(0)
qc.cx(0, 1)
qc.cx(1, 2)
qc.measure([0, 1, 2], [0, 1, 2])

# Explicit pass manager — optimization_level 0-3
pm = generate_preset_pass_manager(optimization_level=2, backend=backend)
isa_circuit = pm.run(qc)   # ISA = Instruction Set Architecture (backend-native)

sampler = SamplerV2(backend)
job = sampler.run([isa_circuit], shots=1024)
counts = job.result()[0].data.meas.get_counts()
print(counts)
```

**Why `isa_circuit`?** ISA stands for Instruction Set Architecture. After transpilation, the circuit is expressed only in gates the specific backend hardware supports. If you run a raw circuit through `SamplerV2` on IBM hardware, it will either fail or silently re-transpile. Always transpile explicitly before running on a real device.

**`optimization_level` reference:**

| Level | What it does | Use case |
|-------|-------------|----------|
| `0`   | Minimal — just maps to hardware gate set | Debugging, fast iteration |
| `1`   | Light optimization, fast compile | Development |
| `2`   | Medium optimization (default) | Most use cases |
| `3`   | Heaviest optimization, slowest compile | Final production run |

---

## Fix 4: Running on IBM Quantum Cloud

The authentication model for IBM Quantum changed alongside the execution model. Old code often used `IBMQ.load_account()` from `qiskit-ibmq-provider`, which is a completely separate package that no longer works. The current stack uses `QiskitRuntimeService` from `qiskit-ibm-runtime`.

**Before (old IBMQ provider):**

```python
# THIS IS BROKEN — qiskit-ibmq-provider is retired
from qiskit import IBMQ, execute

IBMQ.load_account()
provider = IBMQ.get_provider(hub='ibm-q', group='open', project='main')
backend = provider.get_backend('ibm_brisbane')

job = execute(qc, backend, shots=1024)
counts = job.result().get_counts()
```

**After (Qiskit 2.x with qiskit-ibm-runtime):**

```python
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit import QuantumCircuit

# One-time setup: save credentials to disk
# QiskitRuntimeService.save_account(channel="ibm_quantum", token="YOUR_API_TOKEN")

# Load saved credentials and select a backend
service = QiskitRuntimeService(channel="ibm_quantum")
backend = service.least_busy(operational=True, simulator=False, min_num_qubits=2)

print(f"Using backend: {backend.name}")

# Build your circuit
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

# Transpile to backend ISA before running
pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
isa_qc = pm.run(qc)

# Run with SamplerV2
sampler = SamplerV2(backend)
job = sampler.run([isa_qc], shots=1024)

print(f"Job ID: {job.job_id()}")
print("Waiting for result...")

result = job.result()
counts = result[0].data.meas.get_counts()
print(f"Counts: {counts}")
```

**Key changes from the old pattern:**

- `IBMQ.load_account()` → `QiskitRuntimeService(channel="ibm_quantum")`
- `provider.get_backend(name)` → `service.least_busy(...)` or `service.backend(name)`
- `execute(circuit, backend)` → transpile first, then `SamplerV2(backend).run([circuit])`
- No more `qiskit-ibmq-provider` package needed — just `qiskit-ibm-runtime`

---

## Fix 5: Updating qiskit-algorithms Code

If you use VQE, QAOA, or other algorithms from the `qiskit-algorithms` package, those too have updated interfaces in the Qiskit 2.x era. The biggest change: `qiskit.opflow` is gone, replaced by `qiskit.quantum_info.SparsePauliOp`.

**VQE — Before:**

```python
# OLD: opflow-based VQE
from qiskit.algorithms import VQE
from qiskit.algorithms.optimizers import COBYLA
from qiskit.opflow import Z, I
from qiskit.circuit.library import TwoLocal
from qiskit import BasicAer

H = (Z ^ I) + (I ^ Z)   # opflow operator syntax — BROKEN
ansatz = TwoLocal(2, ['ry', 'rz'], 'cx')
optimizer = COBYLA(maxiter=300)
backend = BasicAer.get_backend('statevector_simulator')  # BROKEN

vqe = VQE(ansatz, optimizer=optimizer, quantum_instance=backend)
result = vqe.compute_minimum_eigenvalue(H)
```

**VQE — After:**

```python
from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import COBYLA
from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import TwoLocal
from qiskit.primitives import StatevectorEstimator

# SparsePauliOp replaces opflow operators
H = SparsePauliOp.from_list([("ZI", 1.0), ("IZ", 1.0)])

ansatz = TwoLocal(2, ['ry', 'rz'], 'cx')
optimizer = COBYLA(maxiter=300)
estimator = StatevectorEstimator()  # primitives replace quantum_instance

vqe = VQE(estimator, ansatz, optimizer)
result = vqe.compute_minimum_eigenvalue(H)
print(f"Ground state energy: {result.eigenvalue:.4f}")
```

**QAOA — updated pattern:**

```python
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives import StatevectorSampler

# MaxCut on a 4-node graph
cost_op = SparsePauliOp.from_list([
    ("ZZII", 1.0), ("IZZI", 1.0), ("IIZZ", 1.0), ("ZIIZ", 1.0)
])

sampler = StatevectorSampler()
optimizer = COBYLA(maxiter=200)

qaoa = QAOA(sampler, optimizer, reps=2)
result = qaoa.compute_minimum_eigenvalue(cost_op)
print(f"Best bitstring: {result.best_measurement['bitstring']}")
```

Note: `qiskit-algorithms` is a separate package (`pip install qiskit-algorithms`) and is not part of `qiskit` core. Ensure you have it installed and updated: `pip install qiskit-algorithms --upgrade`.

---

## Fix 6: Aer Simulator Changes

`qiskit-aer` is also a separate package that must be installed and kept up to date independently of `qiskit` core. The simulator interface changed slightly.

**Before:**

```python
from qiskit import BasicAer
backend = BasicAer.get_backend('qasm_simulator')    # BROKEN — BasicAer removed
backend = BasicAer.get_backend('statevector_simulator')  # BROKEN
```

**After:**

```python
from qiskit_aer import AerSimulator

# Statevector simulation (exact, no shots needed for pure state)
statevector_backend = AerSimulator(method='statevector')

# Shot-based simulation (default — mimics quantum hardware sampling)
shot_backend = AerSimulator(method='automatic')  # picks best method

# Noisy simulation (add a noise model from a real device)
from qiskit_aer.noise import NoiseModel
# noise_model = NoiseModel.from_backend(real_backend)
# noisy_backend = AerSimulator(noise_model=noise_model)
```

**Using Aer primitives directly (recommended):**

```python
from qiskit_aer.primitives import SamplerV2, EstimatorV2

# These are drop-in replacements for qiskit.primitives
# but run locally via Aer without needing an explicit backend object
sampler = SamplerV2()           # uses AerSimulator internally
estimator = EstimatorV2()
```

The Aer-native primitives are the most convenient choice for local development — no backend instantiation required, and they support the full SamplerV2/EstimatorV2 interface.

---

## Complete Migration Checklist

Work through this list for each file in your project:

- [ ] Remove `from qiskit import execute` — replace all `execute()` calls
- [ ] Remove `from qiskit import BasicAer` — replace with `from qiskit_aer import AerSimulator`
- [ ] Remove `from qiskit.primitives import Sampler` (V1) — use `SamplerV2` or `StatevectorSampler`
- [ ] Remove `from qiskit.primitives import Estimator` (V1) — use `EstimatorV2` or `StatevectorEstimator`
- [ ] Remove `from qiskit_ibm_runtime import SamplerV1` — use `SamplerV2`
- [ ] Remove `from qiskit_ibm_runtime import EstimatorV1` — use `EstimatorV2`
- [ ] Remove all `from qiskit import IBMQ` and `IBMQ.load_account()` — use `QiskitRuntimeService`
- [ ] Remove all `backend.run(circuit)` patterns — use Sampler/Estimator primitives
- [ ] Replace `from qiskit.opflow import ...` — use `from qiskit.quantum_info import SparsePauliOp`
- [ ] Replace bare `transpile(circuit, backend)` — use `generate_preset_pass_manager()`
- [ ] Update result access: `result.get_counts()` → `result[0].data.meas.get_counts()`
- [ ] Update result access: `result.quasi_dists` → `result[0].data.meas`
- [ ] Verify `qiskit-aer` and `qiskit-algorithms` are installed separately and up to date
- [ ] Test each circuit on `StatevectorSampler()` locally before sending to real hardware
- [ ] For IBM hardware: confirm `QiskitRuntimeService.save_account()` has been called once

---

## Automated Migration — What You Can Script

For large codebases with dozens of files, scanning manually is error-prone. This script checks a directory tree for deprecated patterns and prints file and line numbers so you can tackle them in order.

```python
#!/usr/bin/env python3
"""
qiskit_migration_scan.py
Scans Python files for Qiskit 1.x/0.x patterns that break in Qiskit 2.x.
Usage: python qiskit_migration_scan.py ./src
"""

import sys
import os
import re
from pathlib import Path

DEPRECATED_PATTERNS = [
    (r"from qiskit import execute",             "execute() removed — use SamplerV2 or EstimatorV2"),
    (r"from qiskit import.*BasicAer",           "BasicAer removed — use qiskit_aer.AerSimulator"),
    (r"from qiskit import.*IBMQ",               "IBMQ removed — use QiskitRuntimeService"),
    (r"IBMQ\.load_account",                     "IBMQ.load_account() removed — use QiskitRuntimeService"),
    (r"from qiskit\.primitives import Sampler\b","SamplerV1 removed — use StatevectorSampler or SamplerV2"),
    (r"from qiskit\.primitives import Estimator\b","EstimatorV1 removed — use StatevectorEstimator or EstimatorV2"),
    (r"from qiskit_ibm_runtime import SamplerV1","SamplerV1 removed from runtime — use SamplerV2"),
    (r"from qiskit_ibm_runtime import EstimatorV1","EstimatorV1 removed from runtime — use EstimatorV2"),
    (r"\.quantum_instance\s*=",                 "quantum_instance parameter removed — pass primitive directly"),
    (r"from qiskit\.opflow",                    "qiskit.opflow removed — use qiskit.quantum_info.SparsePauliOp"),
    (r"backend\.run\(",                         "backend.run() deprecated — use Sampler primitive"),
    (r"result\(\)\.get_counts\(",               "Old result format — check if using SamplerV2 result[0].data"),
    (r"result\(\)\.quasi_dists",                "quasi_dists is V1 format — use SamplerV2 result[0].data"),
]

def scan_file(filepath: Path) -> list[tuple[int, str, str]]:
    issues = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return issues

    for i, line in enumerate(text.splitlines(), start=1):
        for pattern, message in DEPRECATED_PATTERNS:
            if re.search(pattern, line):
                issues.append((i, line.strip(), message))
    return issues

def scan_directory(root: str) -> None:
    root_path = Path(root)
    py_files = list(root_path.rglob("*.py"))

    if not py_files:
        print(f"No Python files found in {root}")
        return

    total_issues = 0
    for filepath in sorted(py_files):
        issues = scan_file(filepath)
        if issues:
            print(f"\n{'='*60}")
            print(f"FILE: {filepath}")
            print(f"{'='*60}")
            for line_no, line_text, message in issues:
                print(f"  Line {line_no:4d}: {message}")
                print(f"           > {line_text[:80]}")
                total_issues += 1

    print(f"\n{'='*60}")
    if total_issues == 0:
        print("No deprecated patterns found. Your code looks Qiskit 2.x compatible.")
    else:
        print(f"Found {total_issues} issue(s) across {len(py_files)} file(s) scanned.")
        print("Address each flagged line using the migration guide.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_directory(target)
```

Run it as:

```bash
python qiskit_migration_scan.py ./my_quantum_project
```

Sample output:

```
============================================================
FILE: my_quantum_project/algorithms/vqe_run.py
============================================================
  Line   12: execute() removed — use SamplerV2 or EstimatorV2
             > from qiskit import execute, QuantumCircuit
  Line   45: Old result format — check if using SamplerV2 result[0].data
             > counts = job.result().get_counts(qc)
```

The script does not modify any files — it only reports. You still do the fixes manually using the patterns above, but you will not miss any.

---

## What's NOT Changing

Before you spend time searching for more things to fix, here is what stayed the same in Qiskit 2.x. If your code only uses these APIs, you do not need to change anything:

**Circuit construction is unchanged:**

```python
from qiskit import QuantumCircuit       # same as always
from qiskit.circuit import Parameter    # same
from qiskit.circuit.library import (
    QFT, GroverOperator, TwoLocal,
    RealAmplitudes, EfficientSU2,       # all still here
)

qc = QuantumCircuit(4, 4)
qc.h(0)
qc.cx(0, 1)
qc.ry(0.5, 2)
qc.barrier()
qc.measure_all()                        # all of this works unchanged
```

**Visualization is unchanged:**

```python
qc.draw('mpl')          # Matplotlib diagram — same
qc.draw('text')         # ASCII diagram — same
plot_histogram(counts)  # still works with the new counts dict
```

**Quantum information utilities are unchanged:**

```python
from qiskit.quantum_info import Statevector, DensityMatrix, Operator
from qiskit.quantum_info import random_clifford, random_unitary
```

**All standard gates are unchanged:** `H`, `X`, `Y`, `Z`, `CNOT`, `T`, `S`, `Toffoli`, `SWAP`, `RX/RY/RZ`, `U` — all still importable from `qiskit.circuit.library` or constructable directly on `QuantumCircuit`.

**Third-party packages:** PennyLane, Cirq, and other frameworks that interface with Qiskit through `qiskit-qasm3-import` or circuit conversion utilities are not affected by these execution-layer changes.

---

The migration surface area is smaller than it looks. Once you have replaced `execute()` with the appropriate primitive and updated your result parsing, the vast majority of Qiskit code runs exactly as before. The new primitives model is also genuinely better for the use cases that matter most — running the same algorithm on a local simulator during development and on real IBM hardware for a production run, with zero code changes between them.
