#!/usr/bin/env python3
"""Generate bold, topic-specific SVG thumbnail icons for QubitLogic blog posts.

Each icon is 96x96 viewBox — designed to look great at 96x96px displayed size.
Run before Hugo build: python scripts/generate_cover_images.py
"""

from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUTPUT = ROOT / "static" / "images" / "covers"

SKIP_FILES = {
    "about.md", "privacy.md", "affiliate-disclosure.md",
    "start-here.md", "newsletter.md", "search.md",
}

SECTIONS = {
    "infrastructure":    {"accent": "#00e87a", "secondary": "#38bdf8", "bg": "#0c0e10"},
    "quantum-coding":    {"accent": "#a78bfa", "secondary": "#00e87a", "bg": "#0d0b14"},
    "professional-edge": {"accent": "#38bdf8", "secondary": "#fbbf24", "bg": "#0a0e12"},
}

CATEGORY_COLORS = {
    "tutorial": "#00e87a",
    "benchmark": "#38bdf8",
    "review": "#a78bfa",
    "build": "#fbbf24",
}

# Each motif is SVG inner elements for a 96x96 viewBox.
# Use ACCENT and SECONDARY as placeholders — replaced at render time.
# Icons are bold, high-contrast, immediately recognisable at 96px.
MOTIFS: dict[str, str] = {

    # ── Build article: code editor window ──────────────────────────────
    "cursor_hugo": """
  <rect x="8" y="8" width="80" height="62" rx="7" fill="ACCENT" fill-opacity="0.09" stroke="ACCENT" stroke-width="2.5"/>
  <rect x="8" y="8" width="80" height="19" rx="7" fill="ACCENT" fill-opacity="0.28"/>
  <rect x="8" y="21" width="80" height="6" fill="ACCENT" fill-opacity="0.22"/>
  <circle cx="19" cy="17" r="3.2" fill="#ff5f57"/>
  <circle cx="29" cy="17" r="3.2" fill="#febc2e"/>
  <circle cx="39" cy="17" r="3.2" fill="#28c840"/>
  <line x1="16" y1="37" x2="62" y2="37" stroke="ACCENT" stroke-width="3.5" stroke-linecap="round"/>
  <line x1="16" y1="49" x2="80" y2="49" stroke="SECONDARY" stroke-width="3.5" stroke-linecap="round"/>
  <line x1="16" y1="60" x2="46" y2="60" stroke="ACCENT" stroke-opacity="0.45" stroke-width="3.5" stroke-linecap="round"/>
  <rect x="48" y="56" width="3.5" height="9" rx="1.5" fill="ACCENT"/>""",

    # ── CI/CD: three-node pipeline ──────────────────────────────────────
    "cicd": """
  <circle cx="18" cy="48" r="14" fill="ACCENT" fill-opacity="0.18" stroke="ACCENT" stroke-width="2.5"/>
  <path d="M12 48 L16 52 L24 44" stroke="ACCENT" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <line x1="32" y1="48" x2="42" y2="48" stroke="ACCENT" stroke-opacity="0.5" stroke-width="2.5" stroke-dasharray="4,3" stroke-linecap="round"/>
  <circle cx="52" cy="48" r="14" fill="SECONDARY" fill-opacity="0.18" stroke="SECONDARY" stroke-width="2.5"/>
  <rect x="44" y="41" width="16" height="14" rx="3" stroke="SECONDARY" stroke-width="2" fill="none"/>
  <path d="M48 48 H56 M52 44 V52" stroke="SECONDARY" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="66" y1="48" x2="76" y2="48" stroke="ACCENT" stroke-opacity="0.5" stroke-width="2.5" stroke-dasharray="4,3" stroke-linecap="round"/>
  <circle cx="82" cy="48" r="10" fill="ACCENT" fill-opacity="0.8"/>
  <path d="M77 48 L82 43 L87 48 L82 53 Z" fill="#0c0c0f"/>""",

    # ── Backtesting: candlestick chart ──────────────────────────────────
    "backtest": """
  <line x1="12" y1="84" x2="88" y2="84" stroke="ACCENT" stroke-opacity="0.3" stroke-width="1.5"/>
  <line x1="12" y1="84" x2="12" y2="12" stroke="ACCENT" stroke-opacity="0.3" stroke-width="1.5"/>
  <line x1="30" y1="24" x2="30" y2="76" stroke="SECONDARY" stroke-width="2"/>
  <rect x="24" y="38" width="12" height="28" rx="2" fill="SECONDARY" fill-opacity="0.85"/>
  <line x1="50" y1="16" x2="50" y2="70" stroke="ACCENT" stroke-width="2"/>
  <rect x="44" y="24" width="12" height="30" rx="2" fill="ACCENT" fill-opacity="0.9"/>
  <line x1="70" y1="10" x2="70" y2="62" stroke="ACCENT" stroke-width="2"/>
  <rect x="64" y="16" width="12" height="26" rx="2" fill="ACCENT"/>
  <path d="M24 58 L44 36 L64 22" stroke="ACCENT" stroke-width="2" stroke-dasharray="5,3" fill="none" stroke-linecap="round"/>""",

    # ── DO vs Vultr vs Hetzner: three server bars ───────────────────────
    "vps_three": """
  <rect x="8" y="22" width="24" height="58" rx="5" fill="ACCENT" fill-opacity="0.14" stroke="ACCENT" stroke-width="2"/>
  <circle cx="26" cy="36" r="3.5" fill="ACCENT" fill-opacity="0.8"/>
  <line x1="14" y1="48" x2="26" y2="48" stroke="ACCENT" stroke-opacity="0.5" stroke-width="2" stroke-linecap="round"/>
  <line x1="14" y1="58" x2="26" y2="58" stroke="ACCENT" stroke-opacity="0.5" stroke-width="2" stroke-linecap="round"/>
  <rect x="36" y="12" width="24" height="68" rx="5" fill="SECONDARY" fill-opacity="0.18" stroke="SECONDARY" stroke-width="2"/>
  <circle cx="54" cy="26" r="3.5" fill="SECONDARY" fill-opacity="0.9"/>
  <line x1="42" y1="38" x2="54" y2="38" stroke="SECONDARY" stroke-opacity="0.6" stroke-width="2" stroke-linecap="round"/>
  <line x1="42" y1="48" x2="54" y2="48" stroke="SECONDARY" stroke-opacity="0.6" stroke-width="2" stroke-linecap="round"/>
  <rect x="64" y="30" width="24" height="50" rx="5" fill="ACCENT" fill-opacity="0.12" stroke="ACCENT" stroke-width="2"/>
  <circle cx="82" cy="44" r="3.5" fill="ACCENT" fill-opacity="0.7"/>
  <line x1="70" y1="56" x2="82" y2="56" stroke="ACCENT" stroke-opacity="0.5" stroke-width="2" stroke-linecap="round"/>""",

    # ── DO vs Vultr benchmark: speedometer ─────────────────────────────
    "vps_race": """
  <path d="M14 76 A36 36 0 0 1 82 76" stroke="ACCENT" stroke-opacity="0.18" stroke-width="9" fill="none" stroke-linecap="round"/>
  <path d="M14 76 A36 36 0 0 1 72 40" stroke="ACCENT" stroke-width="9" fill="none" stroke-linecap="round"/>
  <circle cx="48" cy="76" r="7" fill="ACCENT"/>
  <line x1="48" y1="76" x2="72" y2="40" stroke="ACCENT" stroke-width="3.5" stroke-linecap="round"/>
  <circle cx="18" cy="78" r="3" fill="SECONDARY" fill-opacity="0.7"/>
  <circle cx="30" cy="50" r="3" fill="SECONDARY" fill-opacity="0.7"/>
  <circle cx="66" cy="38" r="3" fill="SECONDARY" fill-opacity="0.7"/>
  <circle cx="80" cy="56" r="3" fill="SECONDARY" fill-opacity="0.7"/>""",

    # ── VPS provisioning: terminal window ──────────────────────────────
    "vps_terminal": """
  <rect x="8" y="8" width="80" height="72" rx="8" fill="#080a0c" stroke="ACCENT" stroke-width="2.5"/>
  <rect x="8" y="8" width="80" height="20" rx="8" fill="ACCENT" fill-opacity="0.22"/>
  <rect x="8" y="22" width="80" height="6" fill="ACCENT" fill-opacity="0.18"/>
  <circle cx="20" cy="18" r="3.5" fill="#ff5f57"/>
  <circle cx="31" cy="18" r="3.5" fill="#febc2e"/>
  <circle cx="42" cy="18" r="3.5" fill="#28c840"/>
  <text x="16" y="46" fill="ACCENT" font-family="ui-monospace,monospace" font-size="10" font-weight="600">$ ssh ubuntu@vps</text>
  <text x="16" y="60" fill="SECONDARY" font-family="ui-monospace,monospace" font-size="10">Connected &#x2713;</text>
  <rect x="16" y="63" width="3.5" height="8" rx="1" fill="ACCENT"/>""",

    # ── Nginx: shield with N ────────────────────────────────────────────
    "nginx": """
  <path d="M48 8 L82 24 L82 54 C82 70 66 82 48 90 C30 82 14 70 14 54 L14 24 Z" fill="ACCENT" fill-opacity="0.14" stroke="ACCENT" stroke-width="2.5"/>
  <path d="M32 68 L32 36 L64 68 L64 36" stroke="ACCENT" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>""",

    # ── Python performance: snake + lightning ───────────────────────────
    "python_perf": """
  <circle cx="36" cy="36" r="22" fill="ACCENT" fill-opacity="0.14" stroke="ACCENT" stroke-width="2.5"/>
  <circle cx="60" cy="60" r="22" fill="SECONDARY" fill-opacity="0.14" stroke="SECONDARY" stroke-width="2.5"/>
  <circle cx="43" cy="30" r="4" fill="ACCENT"/>
  <circle cx="53" cy="66" r="4" fill="SECONDARY"/>
  <path d="M54 14 L42 44 L56 44 L44 82" stroke="ACCENT" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>""",

    # ── Quantum-ready tech stack: stacked layers ────────────────────────
    "stack": """
  <rect x="10" y="74" width="76" height="14" rx="4" fill="ACCENT" fill-opacity="0.85"/>
  <rect x="16" y="56" width="64" height="14" rx="4" fill="SECONDARY" fill-opacity="0.75"/>
  <rect x="22" y="38" width="52" height="14" rx="4" fill="ACCENT" fill-opacity="0.55"/>
  <rect x="28" y="20" width="40" height="14" rx="4" fill="SECONDARY" fill-opacity="0.4"/>
  <circle cx="48" cy="16" r="6" fill="ACCENT"/>""",

    # ── Agentic vs manual: robot vs terminal ───────────────────────────
    "agents_vs": """
  <rect x="6" y="28" width="34" height="32" rx="5" fill="ACCENT" fill-opacity="0.15" stroke="ACCENT" stroke-width="2.5"/>
  <rect x="14" y="14" width="18" height="16" rx="4" fill="ACCENT" fill-opacity="0.15" stroke="ACCENT" stroke-width="2"/>
  <circle cx="19" cy="38" r="4.5" fill="ACCENT" fill-opacity="0.85"/>
  <circle cx="31" cy="38" r="4.5" fill="ACCENT" fill-opacity="0.85"/>
  <line x1="18" y1="60" x2="14" y2="76" stroke="ACCENT" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="28" y1="60" x2="32" y2="76" stroke="ACCENT" stroke-width="2.5" stroke-linecap="round"/>
  <text x="48" y="52" text-anchor="middle" fill="#666" font-family="system-ui,sans-serif" font-size="12" font-weight="700">vs</text>
  <rect x="56" y="26" width="34" height="36" rx="5" fill="SECONDARY" fill-opacity="0.15" stroke="SECONDARY" stroke-width="2.5"/>
  <text x="73" y="38" text-anchor="middle" fill="SECONDARY" font-family="ui-monospace,monospace" font-size="9">&gt;_</text>
  <line x1="62" y1="46" x2="84" y2="46" stroke="SECONDARY" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="62" y1="54" x2="78" y2="54" stroke="SECONDARY" stroke-width="2.5" stroke-linecap="round"/>""",

    # ── Audit: magnifying glass over lock ──────────────────────────────
    "audit_lock": """
  <circle cx="38" cy="40" r="24" fill="SECONDARY" fill-opacity="0.1" stroke="SECONDARY" stroke-width="3"/>
  <line x1="56" y1="58" x2="72" y2="74" stroke="SECONDARY" stroke-width="5.5" stroke-linecap="round"/>
  <rect x="28" y="38" width="20" height="18" rx="4" fill="ACCENT" fill-opacity="0.85" stroke="ACCENT" stroke-width="1.5"/>
  <path d="M32 38 V32 C32 26 44 26 44 32 V38" stroke="ACCENT" stroke-width="3" fill="none" stroke-linecap="round"/>
  <circle cx="38" cy="48" r="3.5" fill="#0c0c0f"/>""",

    # ── Enterprise RAG: document → brain ───────────────────────────────
    "rag": """
  <rect x="8" y="16" width="26" height="36" rx="4" fill="SECONDARY" fill-opacity="0.15" stroke="SECONDARY" stroke-width="2"/>
  <line x1="14" y1="26" x2="28" y2="26" stroke="SECONDARY" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="14" y1="34" x2="28" y2="34" stroke="SECONDARY" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="14" y1="42" x2="24" y2="42" stroke="SECONDARY" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="36" y1="34" x2="52" y2="34" stroke="ACCENT" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M48 30 L54 34 L48 38" fill="ACCENT"/>
  <circle cx="70" cy="34" r="20" fill="ACCENT" fill-opacity="0.13" stroke="ACCENT" stroke-width="2"/>
  <circle cx="63" cy="28" r="4.5" fill="ACCENT" fill-opacity="0.85"/>
  <circle cx="77" cy="26" r="3.5" fill="ACCENT" fill-opacity="0.7"/>
  <circle cx="80" cy="40" r="4.5" fill="ACCENT" fill-opacity="0.85"/>
  <circle cx="64" cy="42" r="3.5" fill="ACCENT" fill-opacity="0.65"/>
  <line x1="63" y1="28" x2="77" y2="26" stroke="ACCENT" stroke-width="2"/>
  <line x1="77" y1="26" x2="80" y2="40" stroke="ACCENT" stroke-width="2"/>
  <line x1="80" y1="40" x2="64" y2="42" stroke="ACCENT" stroke-width="2"/>
  <line x1="63" y1="28" x2="80" y2="40" stroke="ACCENT" stroke-width="1.5" stroke-opacity="0.45"/>""",

    # ── Post-quantum crypto: padlock with hex lattice ───────────────────
    "pqc_lock": """
  <path d="M48 8 L62 16 L62 32 L48 40 L34 32 L34 16 Z" fill="SECONDARY" fill-opacity="0.12" stroke="SECONDARY" stroke-opacity="0.4" stroke-width="1.5"/>
  <rect x="32" y="52" width="32" height="28" rx="7" fill="ACCENT" fill-opacity="0.18" stroke="ACCENT" stroke-width="2.5"/>
  <path d="M38 52 V42 C38 30 58 30 58 42 V52" stroke="ACCENT" stroke-width="3" fill="none" stroke-linecap="round"/>
  <circle cx="48" cy="66" r="5.5" fill="ACCENT" fill-opacity="0.9"/>
  <line x1="48" y1="71" x2="48" y2="76" stroke="ACCENT" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="26" cy="24" r="3" fill="SECONDARY" fill-opacity="0.7"/>
  <circle cx="70" cy="24" r="3" fill="SECONDARY" fill-opacity="0.7"/>""",

    # ── Quantum AI certifications: medal + ribbon ───────────────────────
    "certificate": """
  <circle cx="48" cy="40" r="28" fill="ACCENT" fill-opacity="0.14" stroke="ACCENT" stroke-width="2.5"/>
  <circle cx="48" cy="40" r="19" fill="ACCENT" fill-opacity="0.1" stroke="ACCENT" stroke-opacity="0.4" stroke-width="1.5"/>
  <path d="M48 22 L51.8 33.2 L63.6 33.2 L54.2 40.2 L57.9 51.4 L48 44.4 L38.1 51.4 L41.8 40.2 L32.4 33.2 L44.2 33.2 Z" fill="ACCENT" fill-opacity="0.9"/>
  <path d="M36 66 L48 76 L60 66 L56 82 L48 78 L40 82 Z" fill="SECONDARY" fill-opacity="0.85"/>""",

    # ── Top 5 financial APIs: candlestick + API badge ───────────────────
    "finance_api": """
  <line x1="12" y1="82" x2="88" y2="82" stroke="ACCENT" stroke-opacity="0.3" stroke-width="1.5"/>
  <line x1="26" y1="20" x2="26" y2="76" stroke="SECONDARY" stroke-width="2"/>
  <rect x="20" y="32" width="12" height="30" rx="2" fill="SECONDARY" fill-opacity="0.85"/>
  <line x1="46" y1="12" x2="46" y2="76" stroke="ACCENT" stroke-width="2"/>
  <rect x="40" y="20" width="12" height="38" rx="2" fill="ACCENT" fill-opacity="0.9"/>
  <line x1="66" y1="8" x2="66" y2="70" stroke="ACCENT" stroke-width="2"/>
  <rect x="60" y="14" width="12" height="32" rx="2" fill="ACCENT"/>
  <rect x="70" y="66" width="22" height="14" rx="4" fill="SECONDARY" fill-opacity="0.2" stroke="SECONDARY" stroke-width="1.5"/>
  <text x="81" y="76" text-anchor="middle" fill="SECONDARY" font-family="ui-monospace,monospace" font-size="8.5" font-weight="700">API</text>""",

    # ── Grover's algorithm: magnifier + quantum orbits ──────────────────
    "grover": """
  <circle cx="40" cy="40" r="26" fill="ACCENT" fill-opacity="0.1" stroke="ACCENT" stroke-width="3"/>
  <line x1="60" y1="60" x2="78" y2="78" stroke="ACCENT" stroke-width="5.5" stroke-linecap="round"/>
  <ellipse cx="40" cy="40" rx="14" ry="6" stroke="SECONDARY" stroke-width="2" fill="none" stroke-opacity="0.8"/>
  <ellipse cx="40" cy="40" rx="14" ry="6" stroke="SECONDARY" stroke-width="2" fill="none" stroke-opacity="0.8" transform="rotate(60 40 40)"/>
  <ellipse cx="40" cy="40" rx="14" ry="6" stroke="SECONDARY" stroke-width="2" fill="none" stroke-opacity="0.8" transform="rotate(120 40 40)"/>
  <circle cx="40" cy="40" r="4.5" fill="ACCENT"/>""",

    # ── QAOA benchmark: Q gate vs classical bars ────────────────────────
    "qaoa_bench": """
  <rect x="8" y="24" width="32" height="48" rx="5" fill="ACCENT" fill-opacity="0.15" stroke="ACCENT" stroke-width="2"/>
  <text x="24" y="55" text-anchor="middle" fill="ACCENT" font-family="ui-monospace,monospace" font-size="22" font-weight="700">Q</text>
  <line x1="46" y1="16" x2="46" y2="84" stroke="#444" stroke-width="1.5" stroke-dasharray="4,3"/>
  <line x1="52" y1="82" x2="92" y2="82" stroke="SECONDARY" stroke-opacity="0.35" stroke-width="1.5"/>
  <rect x="55" y="46" width="10" height="36" rx="2" fill="SECONDARY" fill-opacity="0.75"/>
  <rect x="69" y="30" width="10" height="52" rx="2" fill="ACCENT" fill-opacity="0.75"/>
  <rect x="83" y="54" width="10" height="28" rx="2" fill="SECONDARY" fill-opacity="0.55"/>""",

    # ── Qiskit 2 migration: 1.x → 2.x ──────────────────────────────────
    "migration": """
  <rect x="8" y="34" width="32" height="32" rx="6" fill="SECONDARY" fill-opacity="0.15" stroke="SECONDARY" stroke-width="2"/>
  <text x="24" y="56" text-anchor="middle" fill="SECONDARY" font-family="ui-monospace,monospace" font-size="14" font-weight="700">1.x</text>
  <line x1="42" y1="50" x2="56" y2="50" stroke="ACCENT" stroke-width="3" stroke-linecap="round"/>
  <path d="M52 44 L60 50 L52 56" stroke="ACCENT" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="58" y="22" width="32" height="44" rx="6" fill="ACCENT" fill-opacity="0.2" stroke="ACCENT" stroke-width="2.5"/>
  <text x="74" y="50" text-anchor="middle" fill="ACCENT" font-family="ui-monospace,monospace" font-size="14" font-weight="700">2.x</text>
  <circle cx="82" cy="28" r="5" fill="ACCENT" fill-opacity="0.9"/>""",

    # ── Qiskit + sklearn hybrid: circuit meets neural net ───────────────
    "hybrid_ml": """
  <line x1="8" y1="32" x2="50" y2="32" stroke="ACCENT" stroke-opacity="0.55" stroke-width="2"/>
  <line x1="8" y1="48" x2="50" y2="48" stroke="ACCENT" stroke-opacity="0.55" stroke-width="2"/>
  <line x1="8" y1="64" x2="50" y2="64" stroke="ACCENT" stroke-opacity="0.55" stroke-width="2"/>
  <rect x="16" y="25" width="14" height="14" rx="3" fill="ACCENT" fill-opacity="0.25" stroke="ACCENT" stroke-width="2"/>
  <text x="23" y="36" text-anchor="middle" fill="ACCENT" font-family="ui-monospace,monospace" font-size="10" font-weight="700">H</text>
  <rect x="32" y="41" width="12" height="14" rx="3" fill="ACCENT" fill-opacity="0.2" stroke="ACCENT" stroke-width="2"/>
  <line x1="50" y1="48" x2="60" y2="32" stroke="SECONDARY" stroke-width="2" stroke-opacity="0.7"/>
  <line x1="50" y1="48" x2="60" y2="64" stroke="SECONDARY" stroke-width="2" stroke-opacity="0.7"/>
  <circle cx="60" cy="32" r="7" fill="SECONDARY" fill-opacity="0.85"/>
  <circle cx="60" cy="64" r="7" fill="SECONDARY" fill-opacity="0.85"/>
  <circle cx="82" cy="48" r="10" fill="SECONDARY"/>
  <line x1="67" y1="32" x2="72" y2="48" stroke="SECONDARY" stroke-width="2"/>
  <line x1="67" y1="64" x2="72" y2="48" stroke="SECONDARY" stroke-width="2"/>""",

    # ── Qiskit vs PennyLane: two shields ───────────────────────────────
    "frameworks_vs": """
  <path d="M24 10 L42 20 L42 44 C42 56 34 64 24 70 C14 64 6 56 6 44 L6 20 Z" fill="ACCENT" fill-opacity="0.15" stroke="ACCENT" stroke-width="2.5"/>
  <text x="24" y="48" text-anchor="middle" fill="ACCENT" font-family="ui-monospace,monospace" font-size="20" font-weight="700">Q</text>
  <text x="48" y="44" text-anchor="middle" fill="#555" font-family="system-ui,sans-serif" font-size="12" font-weight="700">vs</text>
  <path d="M72 10 L90 20 L90 44 C90 56 82 64 72 70 C62 64 54 56 54 44 L54 20 Z" fill="SECONDARY" fill-opacity="0.15" stroke="SECONDARY" stroke-width="2.5"/>
  <text x="72" y="48" text-anchor="middle" fill="SECONDARY" font-family="ui-monospace,monospace" font-size="14" font-weight="700">PL</text>""",

    # ── Quantum optimizer: parabola with minimum ────────────────────────
    "optimizer": """
  <line x1="10" y1="84" x2="88" y2="84" stroke="ACCENT" stroke-opacity="0.3" stroke-width="1.5"/>
  <path d="M12 75 C22 42 36 18 48 14 C60 10 74 28 84 58" stroke="ACCENT" stroke-width="3.5" fill="none" stroke-linecap="round"/>
  <circle cx="48" cy="14" r="8" fill="ACCENT" fill-opacity="0.9"/>
  <path d="M48 7 L50.4 12 L56 12 L51.8 15.2 L53.6 21 L48 17.7 L42.4 21 L44.2 15.2 L40 12 L45.6 12 Z" fill="ACCENT"/>
  <path d="M22 60 L36 34" stroke="SECONDARY" stroke-width="2" stroke-dasharray="3,2" stroke-linecap="round" stroke-opacity="0.7"/>
  <path d="M76 50 L62 26" stroke="SECONDARY" stroke-width="2" stroke-dasharray="3,2" stroke-linecap="round" stroke-opacity="0.7"/>""",

    # ── QML decision: decision diamond ─────────────────────────────────
    "qml_decision": """
  <path d="M48 10 L80 42 L48 74 L16 42 Z" fill="ACCENT" fill-opacity="0.13" stroke="ACCENT" stroke-width="2.5"/>
  <text x="48" y="38" text-anchor="middle" fill="ACCENT" font-family="system-ui,sans-serif" font-size="10" font-weight="700">QML?</text>
  <text x="48" y="52" text-anchor="middle" fill="ACCENT" font-family="ui-monospace,monospace" font-size="12">&#8987;</text>
  <line x1="16" y1="42" x2="8" y2="68" stroke="ACCENT" stroke-width="2.5" stroke-linecap="round"/>
  <text x="4" y="82" fill="ACCENT" font-family="system-ui,sans-serif" font-size="10" font-weight="600">Yes</text>
  <line x1="80" y1="42" x2="88" y2="68" stroke="#555" stroke-width="2.5" stroke-linecap="round"/>
  <text x="78" y="82" fill="#555" font-family="system-ui,sans-serif" font-size="10" font-weight="600">No</text>""",

    # ── Circuit depth optimization: quantum gates ───────────────────────
    "circuit_depth": """
  <line x1="8" y1="28" x2="88" y2="28" stroke="ACCENT" stroke-opacity="0.5" stroke-width="2.5"/>
  <line x1="8" y1="48" x2="88" y2="48" stroke="ACCENT" stroke-opacity="0.5" stroke-width="2.5"/>
  <line x1="8" y1="68" x2="88" y2="68" stroke="ACCENT" stroke-opacity="0.5" stroke-width="2.5"/>
  <rect x="16" y="20" width="16" height="16" rx="3" fill="ACCENT" fill-opacity="0.85" stroke="ACCENT"/>
  <text x="24" y="32" text-anchor="middle" fill="#0c0c0f" font-family="ui-monospace,monospace" font-size="10" font-weight="700">H</text>
  <rect x="44" y="20" width="16" height="16" rx="3" fill="SECONDARY" fill-opacity="0.75" stroke="SECONDARY"/>
  <text x="52" y="32" text-anchor="middle" fill="#0c0c0f" font-family="ui-monospace,monospace" font-size="8" font-weight="700">RZ</text>
  <rect x="28" y="40" width="16" height="16" rx="3" fill="ACCENT" fill-opacity="0.75" stroke="ACCENT"/>
  <text x="36" y="52" text-anchor="middle" fill="#0c0c0f" font-family="ui-monospace,monospace" font-size="10" font-weight="700">X</text>
  <circle cx="62" cy="68" r="8" fill="none" stroke="ACCENT" stroke-width="2.5"/>
  <line x1="54" y1="68" x2="70" y2="68" stroke="ACCENT" stroke-width="2.5"/>
  <line x1="62" y1="60" x2="62" y2="76" stroke="ACCENT" stroke-width="2.5"/>
  <circle cx="62" cy="48" r="4" fill="ACCENT" fill-opacity="0.85"/>
  <line x1="62" y1="52" x2="62" y2="60" stroke="ACCENT" stroke-width="2"/>""",

    # ── TSP simulated annealing: route map ──────────────────────────────
    "tsp": """
  <circle cx="48" cy="14" r="8" fill="ACCENT" fill-opacity="0.9"/>
  <circle cx="78" cy="34" r="8" fill="ACCENT" fill-opacity="0.9"/>
  <circle cx="74" cy="72" r="8" fill="ACCENT" fill-opacity="0.9"/>
  <circle cx="22" cy="72" r="8" fill="SECONDARY" fill-opacity="0.9"/>
  <circle cx="18" cy="34" r="8" fill="ACCENT" fill-opacity="0.7"/>
  <path d="M48 14 L78 34 L74 72 L22 72 L18 34 Z" stroke="ACCENT" stroke-width="2.5" fill="none" stroke-dasharray="6,3" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M58 20 L66 26" stroke="ACCENT" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M63 24 L66 26 L64 29" stroke="ACCENT" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>""",

    # ── Quantum developer toolkit: toolbox ──────────────────────────────
    "toolkit": """
  <rect x="10" y="44" width="76" height="44" rx="7" fill="ACCENT" fill-opacity="0.12" stroke="ACCENT" stroke-width="2.5"/>
  <rect x="28" y="32" width="40" height="16" rx="5" fill="ACCENT" fill-opacity="0.2" stroke="ACCENT" stroke-width="2"/>
  <line x1="10" y1="58" x2="86" y2="58" stroke="ACCENT" stroke-opacity="0.4" stroke-width="2"/>
  <path d="M30 74 L50 54" stroke="ACCENT" stroke-width="4.5" stroke-linecap="round"/>
  <circle cx="54" cy="50" r="9" fill="none" stroke="ACCENT" stroke-width="3"/>
  <circle cx="54" cy="50" r="3.5" fill="ACCENT" fill-opacity="0.8"/>
  <line x1="62" y1="64" x2="74" y2="76" stroke="SECONDARY" stroke-width="4.5" stroke-linecap="round"/>
  <path d="M56 58 L64 66 L60 70 L52 62 Z" fill="SECONDARY" fill-opacity="0.9"/>""",

    # ── Fallback ────────────────────────────────────────────────────────
    "default": """
  <circle cx="48" cy="46" r="32" fill="ACCENT" fill-opacity="0.14" stroke="ACCENT" stroke-width="2.5"/>
  <circle cx="48" cy="46" r="8" fill="ACCENT"/>""",
}

SLUG_MOTIFS: dict[str, str] = {
    "build-technical-blog-cursor-hugo":                   "cursor_hugo",
    "cicd-pipeline-ai-python-scripts":                    "cicd",
    "cost-effective-cloud-architecture-backtesting-pipelines": "backtest",
    "digitalocean-vs-vultr-hetzner-vps-benchmark-2026":   "vps_three",
    "digitalocean-vs-vultr-performance-benchmarks":       "vps_race",
    "how-to-provision-vps-ai-agent-workloads":            "vps_terminal",
    "nginx-reverse-proxy-python-ai-api":                  "nginx",
    "optimizing-python-environment-ubuntu-24-04":         "python_perf",
    "quantum-ready-tech-stack":                           "stack",
    "agentic-workflows-vs-manual-scripts":                "agents_vs",
    "auditing-code-post-quantum-compliance":              "audit_lock",
    "integrating-enterprise-rag-agents":                  "rag",
    "post-quantum-cryptography-api-security":             "pqc_lock",
    "quantum-ai-certification-review":                    "certificate",
    "top-5-apis-real-time-financial-data":                "finance_api",
    "grovers-search-logic-python":                        "grover",
    "qaoa-vs-classical-brute-force-benchmarking":         "qaoa_bench",
    "qiskit-2-migration-guide":                           "migration",
    "qiskit-scikit-learn-hybrid-workflow":                "hybrid_ml",
    "qiskit-vs-pennylane-2026":                           "frameworks_vs",
    "quantum-inspired-optimizer-python":                  "optimizer",
    "quantum-machine-learning-when-to-use":               "qml_decision",
    "simulating-circuit-depth-code-optimization":         "circuit_depth",
    "traveling-salesperson-simulated-annealing":          "tsp",
    "quantum-developer-toolkit":                          "toolkit",
}

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
TITLE_RE = re.compile(r'^title:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)
CATEGORIES_RE = re.compile(
    r'^categories:\s*\[(.+?)\]|^categories:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE
)


def parse_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}
    fm = m.group(1)
    meta: dict = {"title": "", "category": ""}
    if t := TITLE_RE.search(fm):
        meta["title"] = t.group(1).strip()
    if c := CATEGORIES_RE.search(fm):
        raw = (c.group(1) or c.group(2) or "").strip().strip("[]")
        meta["category"] = raw.split(",")[0].strip().strip('"').strip("'")
    return meta


def section_key(md_path: Path) -> str:
    rel = md_path.relative_to(CONTENT)
    return rel.parts[0] if rel.parent != Path(".") else "build"


def section_style(key: str) -> dict:
    return SECTIONS.get(key, {"accent": "#00e87a", "secondary": "#38bdf8", "bg": "#0c0e10"})


def cover_output_path(md_path: Path) -> Path:
    rel = md_path.relative_to(CONTENT)
    return OUTPUT / rel.parent / f"{rel.stem}.svg" if rel.parent != Path(".") \
        else OUTPUT / f"{rel.stem}.svg"


def escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_thumbnail(title: str, style: dict, category: str, motif_key: str) -> str:
    a = style["accent"]
    b = style["secondary"]
    bg = style["bg"]
    cat = category or "article"
    cat_color = CATEGORY_COLORS.get(cat, a)
    cat_label = cat.replace("-", " ").title()

    icon = MOTIFS.get(motif_key, MOTIFS["default"])
    icon = icon.replace("ACCENT", a).replace("SECONDARY", b)

    badge_w = min(len(cat_label) * 5 + 14, 86)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" fill="none" role="img" aria-label="{escape_xml(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="96" y2="96" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0c0c0f"/>
      <stop offset="1" stop-color="{bg}"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="44%" r="52%">
      <stop stop-color="{a}" stop-opacity="0.22"/>
      <stop offset="1" stop-color="{a}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="96" height="96" fill="url(#bg)"/>
  <rect width="96" height="96" fill="url(#glow)"/>
  <rect x="0" y="0" width="3.5" height="96" fill="{a}"/>
{icon}
</svg>
"""


def iter_posts() -> list[Path]:
    return [
        p for p in sorted(CONTENT.rglob("*.md"))
        if p.name not in SKIP_FILES
        and p.name != "_index.md"
        and parse_front_matter(p).get("title")
    ]


def main() -> None:
    posts = iter_posts()
    for md_path in posts:
        meta = parse_front_matter(md_path)
        slug = md_path.stem
        key = section_key(md_path)
        style = section_style(key)
        motif = SLUG_MOTIFS.get(slug, "default")
        svg = build_thumbnail(meta["title"], style, meta.get("category", ""), motif)
        out = cover_output_path(md_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(svg, encoding="utf-8", newline="\n")
        print(f"  {slug}: {motif}")
    print(f"\nGenerated {len(posts)} thumbnails")


if __name__ == "__main__":
    main()
