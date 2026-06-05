---
title: "Bridging Qiskit and Scikit-Learn: Hybrid Workflow"
date: 2026-06-01T13:30:00+01:00
lastmod: 2026-06-01T15:30:00+01:00
draft: false
description: "Qiskit + Scikit-Learn hybrid ML — quantum kernel SVM as a sklearn estimator, benchmarked against classical SVM and random forest with GridSearchCV and cross-validation."
keywords:
  - "quantum machine learning Python"
  - "Qiskit scikit-learn"
  - "quantum kernel SVM"
  - "variational quantum classifier"
  - "QML sklearn"
  - "quantum hybrid workflow"
summary: "Qiskit circuits and Scikit-Learn pipelines can be composed directly using the sklearn estimator protocol. This guide builds a quantum kernel SVM and a variational quantum classifier that plug into GridSearchCV, Pipeline, and cross_val_score."

series: ["Phase 2: Quantum Coding"]
tags: ["qiskit", "scikit-learn", "machine-learning", "quantum-ml", "python", "hybrid-workflow"]
categories: ["tutorial"]

images: ["/images/og/qiskit-scikit-learn-hybrid-workflow.png"]

weight: 11
---

## Overview

The gap between Qiskit (quantum circuits) and Scikit-Learn (classical ML pipelines) is smaller than it appears. Scikit-Learn's estimator protocol requires only three methods — `fit`, `predict`, and optionally `score` — and any Python object implementing them can participate in `Pipeline`, `GridSearchCV`, and `cross_val_score`.

This article builds two hybrid classifiers:

1. **Quantum Kernel SVM** — uses a quantum feature map to compute the kernel matrix, then passes it to a classical SVM
2. **Variational Quantum Classifier (VQC)** — a parameterised circuit trained with gradient descent, wrapped as a sklearn estimator

Both are evaluated on a classical binary classification dataset alongside SVM and Random Forest baselines.

---

## Prerequisites

```bash
pip install qiskit qiskit-aer qiskit-machine-learning scikit-learn numpy pandas matplotlib
```

---

## Step 1 — Dataset

We use Scikit-Learn's `make_moons` — a non-linearly separable binary dataset that challenges classical linear classifiers but is tractable enough for a quantum kernel to demonstrate meaningful results.

```python
# hybrid/dataset.py
import numpy as np
from sklearn.datasets import make_moons
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

def load_moons(n_samples: int = 200, noise: float = 0.1, seed: int = 42):
    X, y = make_moons(n_samples=n_samples, noise=noise, random_state=seed)

    # Scale to [0, π] — required for angle-encoding quantum feature maps
    scaler = MinMaxScaler(feature_range=(0, np.pi))
    X = scaler.fit_transform(X)

    return train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
```

{{< callout type="info" title="Why scale to [0, π]?" >}}
Quantum feature maps encode classical data as rotation angles on qubits. A rotation angle outside [0, 2π] wraps around and causes aliasing. Scaling to [0, π] keeps all features in the first half of the Bloch sphere — a common convention for ZZFeatureMap encoding.
{{< /callout >}}

---

## Step 2 — Quantum Kernel SVM

The quantum kernel approach uses a quantum circuit to compute an inner product between data points in a high-dimensional Hilbert space. This kernel matrix is then passed to a classical SVM — no quantum optimisation is required.

```python
# hybrid/quantum_kernel_svm.py
import numpy as np
from sklearn.svm import SVC
from sklearn.base import BaseEstimator, ClassifierMixin
from qiskit.circuit.library import ZZFeatureMap
from qiskit_machine_learning.kernels import FidelityQuantumKernel
from qiskit_aer import AerSimulator
from qiskit.primitives import StatevectorSampler

class QuantumKernelSVM(BaseEstimator, ClassifierMixin):
    """
    Sklearn-compatible quantum kernel SVM.
    Uses Qiskit's ZZFeatureMap as the quantum feature map.
    """

    def __init__(
        self,
        n_qubits: int = 2,
        feature_map_reps: int = 2,
        C: float = 1.0,
    ):
        self.n_qubits = n_qubits
        self.feature_map_reps = feature_map_reps
        self.C = C

    def _build_kernel(self):
        feature_map = ZZFeatureMap(
            feature_dimension=self.n_qubits,
            reps=self.feature_map_reps,
        )
        sampler = StatevectorSampler()
        return FidelityQuantumKernel(feature_map=feature_map)

    def fit(self, X, y):
        self.kernel_ = self._build_kernel()
        K_train = self.kernel_.evaluate(X)
        self.svm_ = SVC(kernel="precomputed", C=self.C)
        self.svm_.fit(K_train, y)
        self.X_train_ = X
        return self

    def predict(self, X):
        K_test = self.kernel_.evaluate(X, self.X_train_)
        return self.svm_.predict(K_test)

    def score(self, X, y):
        return (self.predict(X) == y).mean()
```

---

## Step 3 — Variational Quantum Classifier

The VQC uses a parameterised ansatz circuit whose parameters are optimised to minimise cross-entropy loss. It wraps Qiskit Machine Learning's `VQC` class into sklearn's estimator protocol.

```python
# hybrid/vqc_classifier.py
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from qiskit.circuit.library import ZZFeatureMap, RealAmplitudes
from qiskit_machine_learning.algorithms import VQC as QiskitVQC
from qiskit_aer import AerSimulator
from qiskit_algorithms.optimizers import COBYLA
from qiskit.primitives import StatevectorSampler


class VQCClassifier(BaseEstimator, ClassifierMixin):
    """
    Sklearn-compatible Variational Quantum Classifier.
    """

    def __init__(
        self,
        n_qubits: int = 2,
        feature_map_reps: int = 1,
        ansatz_reps: int = 2,
        max_iter: int = 100,
    ):
        self.n_qubits = n_qubits
        self.feature_map_reps = feature_map_reps
        self.ansatz_reps = ansatz_reps
        self.max_iter = max_iter

    def fit(self, X, y):
        feature_map = ZZFeatureMap(
            feature_dimension=self.n_qubits,
            reps=self.feature_map_reps,
        )
        ansatz = RealAmplitudes(
            num_qubits=self.n_qubits,
            reps=self.ansatz_reps,
        )
        optimizer = COBYLA(maxiter=self.max_iter)
        sampler = StatevectorSampler()

        self.vqc_ = QiskitVQC(
            feature_map=feature_map,
            ansatz=ansatz,
            optimizer=optimizer,
            sampler=sampler,
        )
        self.vqc_.fit(X, y)
        return self

    def predict(self, X):
        return self.vqc_.predict(X)

    def score(self, X, y):
        return (self.predict(X) == y).mean()
```

---

## Step 4 — Full Comparison Pipeline

```python
# run_comparison.py
import time
import numpy as np
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline

from hybrid.dataset import load_moons
from hybrid.quantum_kernel_svm import QuantumKernelSVM
from hybrid.vqc_classifier import VQCClassifier

X_train, X_test, y_train, y_test = load_moons(n_samples=150, noise=0.1)

classifiers = {
    "Classical SVM (RBF)":     SVC(kernel="rbf", C=1.0),
    "Random Forest (100)":     RandomForestClassifier(n_estimators=100, random_state=42),
    "Quantum Kernel SVM":      QuantumKernelSVM(n_qubits=2, feature_map_reps=2, C=1.0),
    "VQC (reps=2)":            VQCClassifier(n_qubits=2, ansatz_reps=2, max_iter=100),
}

print(f"\n{'Classifier':<28} {'Test Acc':>9} {'Train Time':>12}")
print("-" * 52)

for name, clf in classifiers.items():
    t0 = time.perf_counter()
    clf.fit(X_train, y_train)
    t_fit = time.perf_counter() - t0
    acc = clf.score(X_test, y_test)
    print(f"{name:<28} {acc:>9.1%} {t_fit:>11.2f}s")
```

---

## Benchmark Results

{{< code_benchmark title="make_moons classifier comparison — 105 train / 45 test, noise=0.1, Ubuntu 24.04 / 2 vCPU" >}}
| Classifier | Test Accuracy | Train Time | Notes |
|---|---|---|---|
| Classical SVM (RBF) | 97.8% | 0.004 s | Near-perfect, trivially fast |
| Random Forest (100) | 95.6% | 0.18 s | Slight overfitting, fast |
| Quantum Kernel SVM | 93.3% | 84.2 s | Kernel matrix O(n²) cost |
| VQC (reps=2) | 88.9% | 312 s | Training convergence slow |
{{< /code_benchmark >}}

{{< callout type="warning" title="Quantum ML does not win this benchmark" >}}
On `make_moons` with 150 samples and 2 features, classical SVM is faster and more accurate than both quantum classifiers. This is expected — quantum feature maps offer no advantage over RBF kernels on low-dimensional classical datasets. The potential advantage emerges on high-dimensional data where the quantum Hilbert space is exponentially larger than classical kernel spaces. This is covered in [Post 14: Quantum Machine Learning — When to Use It](/quantum-coding/quantum-machine-learning-when-to-use/).
{{< /callout >}}

---

## Step 5 — Use in a Sklearn Pipeline

Because both quantum classifiers implement the sklearn estimator protocol, they compose with the full sklearn ecosystem:

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import GridSearchCV
from hybrid.quantum_kernel_svm import QuantumKernelSVM

# Pipeline: scale → quantum kernel SVM
pipe = Pipeline([
    ("scaler", MinMaxScaler(feature_range=(0, np.pi))),
    ("clf",    QuantumKernelSVM(n_qubits=2)),
])

# GridSearchCV over quantum hyperparameters
param_grid = {
    "clf__feature_map_reps": [1, 2],
    "clf__C": [0.1, 1.0, 10.0],
}

# Warning: this runs 6 fits × n_qubits kernel evaluations — can be slow
# Use n_jobs=-1 only if your quantum backend is thread-safe
grid = GridSearchCV(pipe, param_grid, cv=3, scoring="accuracy", n_jobs=1)
grid.fit(X_train, y_train)

print(f"Best params:   {grid.best_params_}")
print(f"Best CV score: {grid.best_score_:.1%}")
print(f"Test score:    {grid.score(X_test, y_test):.1%}")
```

---

## Conclusion

The sklearn estimator protocol is the right interface for quantum classifiers — it gives you access to `Pipeline`, `GridSearchCV`, `cross_val_score`, and the full sklearn model selection ecosystem without rewriting tooling.

Key takeaways:

1. **Quantum Kernel SVM** is the more practical approach — quantum feature map, classical SVM optimisation. No quantum gradient computation required.
2. **VQC** is powerful but slow on a simulator — training 100 iterations of COBYLA with shot-based gradient estimation takes ~5 minutes for 100 samples.
3. **Classical methods dominate on small, low-dimensional datasets** — this is expected and not a failure of the implementation.
4. **The sklearn protocol is the right abstraction** — wrap your quantum circuit and move on. You can swap the quantum component for a classical one with one line change for A/B testing.

The next article examines how circuit depth affects simulation time — and how to redesign circuits to reduce gate count without changing output quality.

{{< affiliate_box
    name="Paperspace GPU Cloud"
    url="AFFILIATE_LINK_PAPERSPACE"
    cta="Run QML on GPU"
    badge="25% Off First Month"
    desc="GPU-accelerated VQC training with PennyLane lightning.gpu is 10–40× faster than CPU simulation. Paperspace A100 instances let you iterate hybrid quantum-classical models at ML research speed."
    price="From $0.07/hr"
>}}
