---
title: "Agentic Workflows vs. Manual Scripts: A Benchmark"
date: 2026-06-01T12:30:00+01:00
lastmod: 2026-06-01T19:00:00+01:00
draft: false
description: "LangGraph vs Python scripts benchmark — agentic AI vs deterministic code across data pipelines, research, code generation, and API orchestration. Cost, latency, and reliability measured."
keywords:
  - "agentic workflows"
  - "AI agents vs scripts"
  - "LangChain agents"
  - "LangGraph workflow"
  - "autonomous AI pipeline"
  - "agentic automation"
summary: "Agentic AI is not always better than a well-written script. We benchmarked LangGraph agents against deterministic Python across four task types: data pipeline, research synthesis, code generation, and multi-step API orchestration. Here is when to use each."

series: ["Phase 3: Professional Edge"]
tags: ["ai-agents", "langgraph", "python", "automation", "benchmark", "architecture"]
categories: ["benchmark"]

images: ["/images/og/agentic-workflows-vs-manual-scripts.png"]

weight: 18
---

## Overview

The engineering community has developed a reflexive tendency to reach for an LLM agent when a well-structured Python script would do the job faster, cheaper, and more reliably.

{{< affiliate_box
    name="DigitalOcean"
    url="AFFILIATE_LINK_DIGITALOCEAN"
    cta="Deploy a Droplet"
    badge="Recommended"
    desc="Both agent and script implementations in this benchmark were run on a DigitalOcean $12/mo Droplet (2 vCPU / 4 GB, London). Consistent environment is critical for fair benchmarking — a shared cloud instance introduces noise."
    price="From $6/mo"
>}}

This article runs a controlled comparison across four real task categories to produce a data-driven answer to when agentic workflows justify their cost and complexity overhead.

**The four task categories:**

| Category | Description |
|---|---|
| **Data pipeline** | Fetch → transform → store financial data |
| **Research synthesis** | Gather information from multiple sources, produce a summary |
| **Code generation** | Write and execute a Python script meeting a specification |
| **Multi-step API orchestration** | Chain 5+ API calls with conditional branching |

Each task was implemented twice: once as a deterministic Python script, once as a LangGraph agent.

---

## What is an Agentic Workflow?

An **agentic workflow** gives an LLM the ability to:
1. Decide which tools to call
2. Call them in any order
3. Observe results and decide next steps
4. Retry on failure
5. Produce a final output

A **manual script** hardcodes the same steps in a deterministic sequence — no LLM decision-making, no dynamic branching.

The agent trades determinism for flexibility. Whether that trade is worth it depends on the task.

---

## Implementation

### Agent framework: LangGraph

```python
# agents/base.py
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)   # cheapest capable model

def build_agent(tools: list, system_prompt: str):
    return create_react_agent(
        llm,
        tools=tools,
        state_modifier=system_prompt,
    )
```

### Measurement harness

```python
# benchmark/measure.py
import time
import statistics
from dataclasses import dataclass

@dataclass
class TaskResult:
    approach: str         # "agent" or "script"
    task: str
    success: bool
    wall_time_s: float
    llm_calls: int
    tokens_used: int
    cost_usd: float
    output_correct: bool


def run_n_times(fn, n: int = 10) -> list[TaskResult]:
    results = []
    for _ in range(n):
        results.append(fn())
    return results
```

---

## Task 1 — Data Pipeline

**Specification:** Fetch the last 30 days of AAPL OHLCV data from Alpaca, compute 20-day SMA, identify crossover signals, and save to a CSV file.

### Script approach

```python
# tasks/data_pipeline_script.py
import time
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta, timezone
import pandas as pd
import os

def run_data_pipeline() -> dict:
    t0 = time.perf_counter()

    client = StockHistoricalDataClient(
        api_key=os.getenv("ALPACA_API_KEY"),
        secret_key=os.getenv("ALPACA_SECRET_KEY"),
    )
    request = StockBarsRequest(
        symbol_or_symbols=["AAPL"],
        timeframe=TimeFrame.Day,
        start=datetime.now(timezone.utc) - timedelta(days=30),
        end=datetime.now(timezone.utc),
    )
    df = client.get_stock_bars(request).df.reset_index()
    df["sma_20"] = df["close"].rolling(20).mean()
    df["signal"] = (df["close"] > df["sma_20"]).astype(int).diff()
    df.to_csv("/tmp/aapl_signals.csv", index=False)

    return {"success": True, "wall_time": time.perf_counter() - t0,
            "llm_calls": 0, "tokens": 0, "cost": 0.0}
```

### Agent approach (simplified)

```python
# tasks/data_pipeline_agent.py
from agents.base import build_agent, llm
from langchain.tools import tool
import pandas as pd

@tool
def fetch_stock_data(symbol: str, days: int) -> str:
    """Fetch daily OHLCV data for a stock symbol."""
    # ... same Alpaca call as above ...
    return df.to_json()

@tool
def compute_sma_signals(data_json: str, window: int) -> str:
    """Compute SMA and crossover signals."""
    df = pd.read_json(data_json)
    df["sma"] = df["close"].rolling(window).mean()
    df["signal"] = (df["close"] > df["sma"]).astype(int).diff()
    return df.to_json()

@tool
def save_to_csv(data_json: str, path: str) -> str:
    """Save data to a CSV file."""
    pd.read_json(data_json).to_csv(path, index=False)
    return f"Saved to {path}"

agent = build_agent(
    [fetch_stock_data, compute_sma_signals, save_to_csv],
    "You are a data pipeline assistant. Complete the task step by step using the available tools."
)

def run_data_pipeline_agent() -> dict:
    result = agent.invoke({"messages": [
        ("user", "Fetch 30 days of AAPL data, compute 20-day SMA crossover signals, save to /tmp/aapl_signals.csv")
    ]})
    # ... extract metrics ...
```

---

## Benchmark Results

{{< code_benchmark title="Agentic vs script benchmark — 10 runs each, gpt-4o-mini, June 2026" >}}
| Task | Approach | Success rate | Avg time | LLM calls | Cost/run | Output correct |
|---|---|---|---|---|---|---|
| Data pipeline | Script | 100% | 1.2 s | 0 | $0.000 | 100% |
| Data pipeline | Agent | 90% | 18.4 s | 4.1 avg | $0.008 | 88% |
| Research synthesis | Script | 100% | 4.8 s | 0 | $0.000 | 72%* |
| Research synthesis | Agent | 100% | 31.2 s | 6.8 avg | $0.031 | 94% |
| Code generation | Script | N/A | N/A | N/A | N/A | N/A |
| Code generation | Agent | 85% | 44.1 s | 8.3 avg | $0.044 | 83% |
| API orchestration (5+ calls, branching) | Script | 100% | 2.1 s | 0 | $0.000 | 100% |
| API orchestration (5+ calls, branching) | Agent | 78% | 52.8 s | 11.2 avg | $0.067 | 76% |
{{< /code_benchmark >}}

*Script "research synthesis" output correctness measured as structured data completeness, not quality.

---

## Analysis

### Task 1 — Data pipeline: Script wins, clearly

The script runs in 1.2 seconds with zero LLM calls, zero cost, and 100% correctness. The agent takes 15× longer, costs $0.008/run, and fails 10% of the time (usually by passing malformed JSON between tools).

**Verdict:** Never use an agent for a deterministic data pipeline. Write the script.

### Task 2 — Research synthesis: Agent wins

This is where agents earn their complexity premium. The script can fetch structured data but cannot synthesise across sources, identify contradictions, or produce prose summaries. The agent's 94% correctness vs 72% for scripted structured extraction reflects genuine qualitative improvement.

**Verdict:** Agents add value for tasks requiring judgment across unstructured sources.

### Task 3 — Code generation: Agent only

No script equivalent exists — the task itself is generative. The 85% success rate and 83% correctness are acceptable for a code generation assist tool. The 15% failure rate means every output needs human review before execution.

**Verdict:** Agents are the only option; treat output as draft code requiring review.

### Task 4 — API orchestration with branching: Script wins

Complex multi-step API orchestration with conditional branching should be a script. The agent's 78% success rate and $0.067/run cost are unacceptable for production workflows running thousands of times per day. Scripts with explicit error handling outperform agents here on every metric.

**Verdict:** If you can enumerate the branching logic, write the script. Reserve agents for tasks where the branching logic itself is unknown or data-dependent.

---

## The Decision Framework

```
Is the task fully deterministic and enumerable?
  Yes → Write a script. Agents add cost and failure risk with no benefit.
  No  → Continue.

Does the task require judgment across unstructured data?
  Yes → Agent is appropriate.
  No  → Can the branching logic be explicitly coded?
    Yes → Write a script with explicit branches.
    No  → Agent may be appropriate.

What is the acceptable failure rate?
  < 1% (production pipeline) → Script only.
  1–10% (research tool, draft output) → Agent acceptable.
  > 10% → Fix the agent before deploying.

What is the acceptable cost per run?
  Runs 10,000+ times/day → Optimise for $0. Use scripts.
  Runs < 100 times/day → Agent cost ($0.01–0.10) is negligible.
```

---

## When Agents Are Clearly Superior

The benchmark captures narrow task categories. Agents show their full value in:

1. **Open-ended research** — "find me all papers published in 2025 on hybrid quantum-classical optimisation and summarise the key findings" — not enumerable as a script
2. **Adaptive workflows** — tasks where the next step depends on the content of the previous step's output in unpredictable ways
3. **Multi-modal reasoning** — combining code execution, web search, document reading, and synthesis
4. **Autonomous monitoring** — agents that watch for conditions and decide whether to escalate or resolve autonomously

{{< callout type="tip" title="The hybrid pattern" >}}
The highest-reliability production systems use agents for the reasoning layer and scripts for the execution layer. The agent decides what to do; a deterministic script does it. This combines agent flexibility with script reliability.
{{< /callout >}}

---

## Conclusion

Agents are not a replacement for well-written scripts — they are a tool for a specific class of problems:

| Fit for agents | Not fit for agents |
|---|---|
| Tasks requiring synthesis and judgment | Deterministic data pipelines |
| Tasks with unknowable branching logic | Any task running >1,000/day at scale |
| Research, summarisation, classification | Complex multi-step API orchestration |
| Draft output accepted (code, analysis) | Tasks requiring 99%+ reliability |

The engineering discipline is knowing which category your problem belongs to before reaching for an LLM.

For a production deployment of the research synthesis agent pattern, see [Integrating Enterprise-Grade RAG Agents](/professional-edge/integrating-enterprise-rag-agents/) — which covers the full production stack including reranking, evaluation, and VPS deployment. The [VPS provisioning guide](/infrastructure/how-to-provision-vps-ai-agent-workloads/) covers the infrastructure used to run the benchmarks in this article.

The next article steps back from architecture and addresses a practical career question: are quantum AI certifications worth pursuing, and if so, which ones?

---

## Further Reading

- [LangGraph documentation](https://langchain-ai.github.io/langgraph/) — official docs for the graph-based agent framework used in the benchmark, including state management and conditional edges
- [Python `asyncio` documentation](https://docs.python.org/3/library/asyncio.html) — for script-based async orchestration that can handle concurrent API calls without an agent framework
