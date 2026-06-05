#!/usr/bin/env python3
"""Generate small topic-specific SVG thumbnails for QubitLogic blog posts.

Thumbnails are used in post lists (left column). Run before Hugo build:
    python scripts/generate_cover_images.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUTPUT = ROOT / "static" / "images" / "covers"

SKIP_FILES = {
    "about.md",
    "privacy.md",
    "affiliate-disclosure.md",
    "start-here.md",
    "newsletter.md",
    "search.md",
}

SECTIONS = {
    "infrastructure": {"accent": "#00e87a", "secondary": "#38bdf8", "bg_end": "#131a22"},
    "quantum-coding": {"accent": "#a78bfa", "secondary": "#00e87a", "bg_end": "#120f1a"},
    "professional-edge": {"accent": "#38bdf8", "secondary": "#fbbf24", "bg_end": "#0f1418"},
}

CATEGORY_COLORS = {
    "tutorial": "#00e87a",
    "benchmark": "#38bdf8",
    "review": "#a78bfa",
    "build": "#fbbf24",
}

# Unique icon per post slug — matched to article topic
SLUG_MOTIFS: dict[str, str] = {
    "build-technical-blog-cursor-hugo": "cursor_hugo",
    "cicd-pipeline-ai-python-scripts": "cicd",
    "cost-effective-cloud-architecture-backtesting-pipelines": "backtest",
    "digitalocean-vs-vultr-hetzner-vps-benchmark-2026": "vps_three",
    "digitalocean-vs-vultr-performance-benchmarks": "vps_race",
    "how-to-provision-vps-ai-agent-workloads": "vps_terminal",
    "nginx-reverse-proxy-python-ai-api": "nginx",
    "optimizing-python-environment-ubuntu-24-04": "python_perf",
    "quantum-ready-tech-stack": "stack",
    "agentic-workflows-vs-manual-scripts": "agents_vs",
    "auditing-code-post-quantum-compliance": "audit_lock",
    "integrating-enterprise-rag-agents": "rag",
    "post-quantum-cryptography-api-security": "pqc_lock",
    "quantum-ai-certification-review": "certificate",
    "top-5-apis-real-time-financial-data": "finance_api",
    "grovers-search-logic-python": "grover",
    "qaoa-vs-classical-brute-force-benchmarking": "qaoa_bench",
    "qiskit-2-migration-guide": "migration",
    "qiskit-scikit-learn-hybrid-workflow": "hybrid_ml",
    "qiskit-vs-pennylane-2026": "frameworks_vs",
    "quantum-inspired-optimizer-python": "optimizer",
    "quantum-machine-learning-when-to-use": "qml_decision",
    "simulating-circuit-depth-code-optimization": "circuit_depth",
    "traveling-salesperson-simulated-annealing": "tsp",
    "quantum-developer-toolkit": "toolkit",
}

TAG_MOTIFS: dict[str, str] = {
    "nginx": "nginx",
    "cicd": "cicd",
    "github-actions": "cicd",
    "vps": "vps_terminal",
    "benchmark": "vps_race",
    "benchmarks": "vps_race",
    "qiskit": "circuit_depth",
    "grovers-algorithm": "grover",
    "qaoa": "optimizer",
    "pennylane": "frameworks_vs",
    "rag": "rag",
    "langgraph": "agents_vs",
    "post-quantum": "pqc_lock",
    "cryptography": "pqc_lock",
    "financial-data": "finance_api",
    "cursor": "cursor_hugo",
    "hugo": "cursor_hugo",
    "newsletter": "cursor_hugo",
    "backtesting": "backtest",
    "optimization": "optimizer",
    "toolkit": "toolkit",
}

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
TITLE_RE = re.compile(r'^title:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)
CATEGORIES_RE = re.compile(
    r'^categories:\s*\[(.+?)\]|^categories:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE
)
TAGS_RE = re.compile(r'^tags:\s*\[(.+?)\]', re.MULTILINE)


def parse_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}
    fm = match.group(1)
    meta: dict = {"title": "", "category": "", "tags": []}
    if m := TITLE_RE.search(fm):
        meta["title"] = m.group(1).strip()
    if m := CATEGORIES_RE.search(fm):
        raw = (m.group(1) or m.group(2) or "").strip().strip("[]")
        meta["category"] = raw.split(",")[0].strip().strip('"').strip("'")
    if m := TAGS_RE.search(fm):
        raw = m.group(1)
        meta["tags"] = [
            t.strip().strip('"').strip("'")
            for t in raw.split(",")
            if t.strip()
        ]
    return meta


def motif_key(slug: str, tags: list[str]) -> str:
    if slug in SLUG_MOTIFS:
        return SLUG_MOTIFS[slug]
    for tag in tags:
        if tag in TAG_MOTIFS:
            return TAG_MOTIFS[tag]
    return "default"


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def draw_motif(key: str, accent: str, secondary: str) -> str:
    cx, cy = 200, 135
    motifs = {
        "cursor_hugo": f"""
  <rect x="145" y="88" width="110" height="78" rx="8" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.08"/>
  <path d="M158 108 L158 148 M158 108 L188 108 L188 128" stroke="{accent}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <text x="200" y="132" text-anchor="middle" fill="{secondary}" font-family="monospace" font-size="22" font-weight="700">&lt;/&gt;</text>
  <circle cx="238" cy="100" r="5" fill="{accent}"/>""",
        "cicd": f"""
  <circle cx="155" cy="135" r="18" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.15"/>
  <path d="M185 135 H225 M215 125 L225 135 L215 145" stroke="{secondary}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <rect x="235" y="117" width="46" height="36" rx="6" stroke="{accent}" stroke-width="2" fill="none"/>
  <path d="M248 135 H268" stroke="{accent}" stroke-width="2"/>""",
        "backtest": f"""
  <path d="M130 175 L160 145 L190 158 L220 118 L250 130 L270 108" stroke="{secondary}" stroke-width="2.5" fill="none"/>
  <rect x="130" y="95" width="28" height="22" rx="4" stroke="{accent}" stroke-width="1.5" fill="{accent}" fill-opacity="0.12"/>
  <rect x="168" y="95" width="28" height="22" rx="4" stroke="{accent}" stroke-width="1.5" fill="{accent}" fill-opacity="0.12"/>
  <rect x="206" y="95" width="28" height="22" rx="4" stroke="{accent}" stroke-width="1.5" fill="{accent}" fill-opacity="0.12"/>""",
        "vps_three": f"""
  <rect x="128" y="100" width="44" height="70" rx="6" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.1"/>
  <rect x="178" y="90" width="44" height="80" rx="6" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.1"/>
  <rect x="228" y="108" width="44" height="62" rx="6" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.1"/>
  <line x1="136" y1="118" x2="164" y2="118" stroke="{accent}" stroke-width="2"/>
  <line x1="186" y1="108" x2="214" y2="108" stroke="{secondary}" stroke-width="2"/>
  <line x1="236" y1="126" x2="264" y2="126" stroke="{accent}" stroke-width="2"/>""",
        "vps_race": f"""
  <rect x="125" y="108" width="55" height="62" rx="6" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.12"/>
  <rect x="220" y="98" width="55" height="72" rx="6" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.12"/>
  <path d="M195 135 L210 125 L210 145 Z" fill="{accent}"/>""",
        "vps_terminal": f"""
  <rect x="130" y="92" width="140" height="86" rx="8" stroke="{accent}" stroke-width="2" fill="#0a0a0c"/>
  <path d="M148 118 L168 135 L148 152" stroke="{accent}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <line x1="178" y1="152" x2="240" y2="152" stroke="{secondary}" stroke-width="2" stroke-linecap="round"/>""",
        "nginx": f"""
  <rect x="145" y="95" width="110" height="28" rx="4" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.15"/>
  <rect x="155" y="133" width="90" height="28" rx="4" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.12"/>
  <rect x="165" y="171" width="70" height="28" rx="4" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.1"/>
  <path d="M200 95 V171" stroke="{accent}" stroke-width="1" stroke-opacity="0.4"/>""",
        "python_perf": f"""
  <path d="M175 108 C175 98 185 92 200 92 C215 92 225 98 225 108 V122 C225 132 215 138 200 138 H190 V152 H210" stroke="{accent}" stroke-width="2.5" fill="none"/>
  <circle cx="200" cy="115" r="4" fill="{secondary}"/>
  <path d="M155 175 L175 155 L195 168 L215 142 L245 158" stroke="{secondary}" stroke-width="2" fill="none"/>""",
        "stack": f"""
  <rect x="140" y="168" width="120" height="18" rx="4" stroke="{accent}" stroke-width="1.5" fill="{accent}" fill-opacity="0.15"/>
  <rect x="150" y="142" width="100" height="18" rx="4" stroke="{secondary}" stroke-width="1.5" fill="{secondary}" fill-opacity="0.12"/>
  <rect x="160" y="116" width="80" height="18" rx="4" stroke="{accent}" stroke-width="1.5" fill="{accent}" fill-opacity="0.1"/>
  <circle cx="200" cy="102" r="10" stroke="{accent}" stroke-width="2" fill="none"/>""",
        "agents_vs": f"""
  <circle cx="165" cy="135" r="28" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.1"/>
  <circle cx="165" cy="128" r="8" fill="{accent}"/>
  <path d="M155 148 H175 M160 158 H170" stroke="{accent}" stroke-width="2" stroke-linecap="round"/>
  <rect x="215" y="108" width="70" height="54" rx="6" stroke="{secondary}" stroke-width="2" fill="none"/>
  <line x1="225" y1="122" x2="275" y2="122" stroke="{secondary}" stroke-width="2"/>
  <line x1="225" y1="136" x2="265" y2="136" stroke="{secondary}" stroke-width="1.5" stroke-opacity="0.6"/>
  <line x1="225" y1="150" x2="255" y2="150" stroke="{secondary}" stroke-width="1.5" stroke-opacity="0.6"/>""",
        "audit_lock": f"""
  <circle cx="175" cy="140" r="32" stroke="{secondary}" stroke-width="2" fill="none"/>
  <path d="M188 140 L170 158 L160 148" stroke="{accent}" stroke-width="3" fill="none" stroke-linecap="round"/>
  <rect x="220" y="118" width="50" height="44" rx="8" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.1"/>
  <path d="M245 118 V108 C245 98 255 92 245 92 H240" stroke="{accent}" stroke-width="2" fill="none"/>""",
        "rag": f"""
  <rect x="125" y="108" width="42" height="54" rx="4" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.08"/>
  <rect x="175" y="100" width="42" height="54" rx="4" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.08"/>
  <path d="M167 135 H185 M217 135 H235" stroke="{accent}" stroke-width="2"/>
  <circle cx="255" cy="135" r="22" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.12"/>
  <circle cx="255" cy="135" r="6" fill="{accent}"/>""",
        "pqc_lock": f"""
  <rect x="168" y="128" width="64" height="48" rx="8" stroke="{accent}" stroke-width="2.5" fill="{accent}" fill-opacity="0.12"/>
  <path d="M184 128 V112 C184 98 216 98 216 112 V128" stroke="{accent}" stroke-width="2.5" fill="none"/>
  <circle cx="200" cy="152" r="6" fill="{secondary}"/>
  <ellipse cx="200" cy="88" rx="40" ry="12" stroke="{secondary}" stroke-width="1.5" fill="none" stroke-opacity="0.5"/>""",
        "certificate": f"""
  <rect x="145" y="95" width="110" height="80" rx="6" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.08"/>
  <circle cx="200" cy="125" r="18" stroke="{accent}" stroke-width="2" fill="none"/>
  <path d="M192 125 L198 131 L210 119" stroke="{accent}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <line x1="165" y1="155" x2="235" y2="155" stroke="{accent}" stroke-width="2" stroke-opacity="0.5"/>""",
        "finance_api": f"""
  <line x1="130" y1="175" x2="270" y2="175" stroke="{accent}" stroke-opacity="0.3" stroke-width="1"/>
  <rect x="145" y="148" width="14" height="27" fill="{accent}" fill-opacity="0.7"/>
  <rect x="168" y="132" width="14" height="43" fill="{secondary}" fill-opacity="0.7"/>
  <rect x="191" y="158" width="14" height="17" fill="{accent}" fill-opacity="0.5"/>
  <rect x="214" y="122" width="14" height="53" fill="{secondary}" fill-opacity="0.8"/>
  <rect x="237" y="140" width="14" height="35" fill="{accent}" fill-opacity="0.6"/>
  <path d="M130 108 H270" stroke="{secondary}" stroke-width="2"/>""",
        "grover": f"""
  <ellipse cx="200" cy="135" rx="70" ry="24" stroke="{accent}" stroke-width="2" fill="none" transform="rotate(-25 200 135)"/>
  <ellipse cx="200" cy="135" rx="70" ry="24" stroke="{secondary}" stroke-width="2" fill="none" transform="rotate(25 200 135)"/>
  <circle cx="200" cy="135" r="8" fill="{accent}"/>
  <path d="M248 108 L268 88 M268 88 L268 108 M268 88 L248 88" stroke="{secondary}" stroke-width="2.5" fill="none" stroke-linecap="round"/>""",
        "qaoa_bench": f"""
  <path d="M130 170 L170 130 L210 148 L250 108" stroke="{accent}" stroke-width="2.5" fill="none"/>
  <rect x="215" y="108" width="70" height="62" rx="4" stroke="{secondary}" stroke-width="1.5" fill="none"/>
  <line x1="225" y1="122" x2="275" y2="122" stroke="{secondary}" stroke-opacity="0.5"/>
  <line x1="225" y1="138" x2="275" y2="138" stroke="{secondary}" stroke-opacity="0.5"/>
  <line x1="225" y1="154" x2="275" y2="154" stroke="{secondary}" stroke-opacity="0.5"/>""",
        "migration": f"""
  <rect x="130" y="118" width="50" height="40" rx="6" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.1"/>
  <path d="M195 138 H215 M210 128 L220 138 L210 148" stroke="{accent}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <rect x="230" y="108" width="50" height="50" rx="6" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.12"/>
  <text x="255" y="140" text-anchor="middle" fill="{accent}" font-family="monospace" font-size="16" font-weight="700">2.x</text>""",
        "hybrid_ml": f"""
  <circle cx="160" cy="135" r="30" stroke="{accent}" stroke-width="2" fill="none"/>
  <line x1="160" y1="105" x2="160" y2="165" stroke="{accent}" stroke-opacity="0.5"/>
  <line x1="130" y1="135" x2="190" y2="135" stroke="{accent}" stroke-opacity="0.5"/>
  <path d="M205 135 H235" stroke="{secondary}" stroke-width="2.5"/>
  <rect x="235" y="110" width="50" height="50" rx="6" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.1"/>
  <path d="M248 145 L262 128 L275 152" stroke="{secondary}" stroke-width="2" fill="none"/>""",
        "frameworks_vs": f"""
  <rect x="125" y="108" width="55" height="55" rx="8" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.1"/>
  <text x="152" y="142" text-anchor="middle" fill="{accent}" font-family="monospace" font-size="14" font-weight="700">Q</text>
  <text x="200" y="142" text-anchor="middle" fill="#8888a0" font-family="system-ui" font-size="18" font-weight="700">vs</text>
  <rect x="220" y="108" width="55" height="55" rx="8" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.1"/>
  <text x="247" y="142" text-anchor="middle" fill="{secondary}" font-family="monospace" font-size="14" font-weight="700">PL</text>""",
        "optimizer": f"""
  <path d="M130 168 Q165 108 200 128 T270 98" stroke="{accent}" stroke-width="2.5" fill="none"/>
  <circle cx="200" cy="128" r="8" fill="{accent}"/>
  <circle cx="165" cy="145" r="5" fill="{secondary}" fill-opacity="0.7"/>
  <circle cx="235" cy="112" r="5" fill="{secondary}" fill-opacity="0.7"/>""",
        "qml_decision": f"""
  <path d="M200 95 V175 M160 135 H240" stroke="{accent}" stroke-opacity="0.4" stroke-width="2"/>
  <circle cx="160" cy="115" r="16" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.15"/>
  <circle cx="240" cy="115" r="16" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.15"/>
  <circle cx="160" cy="175" r="16" stroke="{secondary}" stroke-width="2" fill="{secondary}" fill-opacity="0.15"/>
  <circle cx="240" cy="175" r="16" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.15"/>""",
        "circuit_depth": f"""
  <line x1="145" y1="175" x2="145" y2="105" stroke="{accent}" stroke-width="3"/>
  <line x1="175" y1="175" x2="175" y2="115" stroke="{accent}" stroke-width="3"/>
  <line x1="205" y1="175" x2="205" y2="125" stroke="{secondary}" stroke-width="3"/>
  <line x1="235" y1="175" x2="235" y2="135" stroke="{secondary}" stroke-width="3"/>
  <line x1="265" y1="175" x2="265" y2="145" stroke="{accent}" stroke-width="3"/>
  <line x1="140" y1="140" x2="270" y2="140" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.4"/>""",
        "tsp": f"""
  <circle cx="155" cy="118" r="8" fill="{accent}"/>
  <circle cx="245" cy="108" r="8" fill="{accent}"/>
  <circle cx="265" cy="168" r="8" fill="{secondary}"/>
  <circle cx="145" cy="168" r="8" fill="{secondary}"/>
  <circle cx="200" cy="145" r="8" fill="{accent}" fill-opacity="0.6"/>
  <path d="M155 118 L245 108 L265 168 L145 168 Z" stroke="{accent}" stroke-width="2" fill="none" stroke-dasharray="6 4"/>""",
        "toolkit": f"""
  <rect x="135" y="100" width="130" height="70" rx="8" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.08"/>
  <rect x="148" y="88" width="36" height="18" rx="4" fill="{accent}" fill-opacity="0.25"/>
  <line x1="155" y1="130" x2="245" y2="130" stroke="{secondary}" stroke-width="2"/>
  <line x1="155" y1="148" x2="220" y2="148" stroke="{accent}" stroke-width="2" stroke-opacity="0.5"/>
  <circle cx="230" cy="155" r="8" stroke="{secondary}" stroke-width="2" fill="none"/>""",
        "default": f"""
  <circle cx="{cx}" cy="{cy}" r="42" stroke="{accent}" stroke-width="2" fill="{accent}" fill-opacity="0.1"/>
  <circle cx="{cx}" cy="{cy}" r="8" fill="{accent}"/>""",
    }
    return motifs.get(key, motifs["default"])


def build_thumbnail(
    title: str,
    section: dict[str, str],
    category: str,
    motif: str,
    label: str,
) -> str:
    cat = category or "article"
    cat_color = CATEGORY_COLORS.get(cat, section["accent"])

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" fill="none" role="img" aria-label="{escape_xml(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="400" y2="300" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0c0c0f"/>
      <stop offset="1" stop-color="{section['bg_end']}"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="45%" r="55%">
      <stop stop-color="{section['accent']}" stop-opacity="0.18"/>
      <stop offset="1" stop-color="{section['accent']}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="400" height="300" fill="url(#bg)"/>
  <rect width="400" height="300" fill="url(#glow)"/>
  <rect x="0" y="0" width="4" height="300" fill="{section['accent']}"/>
{draw_motif(motif, section['accent'], section['secondary'])}
  <rect x="16" y="258" width="{min(len(label) * 7 + 20, 180)}" height="22" rx="11" fill="{cat_color}" fill-opacity="0.15" stroke="{cat_color}" stroke-opacity="0.35"/>
  <text x="26" y="273" fill="{cat_color}" font-family="Inter, system-ui, sans-serif" font-size="11" font-weight="600">{escape_xml(label[:22])}</text>
</svg>
"""


def section_key(md_path: Path) -> str:
    rel = md_path.relative_to(CONTENT)
    if rel.parent != Path("."):
        return rel.parts[0]
    return "build" if "build" in rel.stem else "site"


def section_style(key: str) -> dict[str, str]:
    return SECTIONS.get(
        key,
        {"accent": "#00e87a", "secondary": "#38bdf8", "bg_end": "#131a22"},
    )


def cover_output_path(md_path: Path) -> Path:
    rel = md_path.relative_to(CONTENT)
    if rel.parent == Path("."):
        return OUTPUT / f"{rel.stem}.svg"
    return OUTPUT / rel.parent / f"{rel.stem}.svg"


def primary_label(tags: list[str], category: str) -> str:
    if tags:
        return tags[0].replace("-", " ")
    return category or "article"


def iter_posts() -> list[Path]:
    posts: list[Path] = []
    for path in sorted(CONTENT.rglob("*.md")):
        if path.name in SKIP_FILES or path.name == "_index.md":
            continue
        if parse_front_matter(path).get("title"):
            posts.append(path)
    return posts


def main() -> None:
    posts = iter_posts()
    for md_path in posts:
        meta = parse_front_matter(md_path)
        slug = md_path.stem
        key = section_key(md_path)
        style = section_style(key)
        motif = motif_key(slug, meta.get("tags", []))
        label = primary_label(meta.get("tags", []), meta.get("category", ""))
        svg = build_thumbnail(
            meta["title"],
            style,
            meta.get("category", ""),
            motif,
            label,
        )
        out = cover_output_path(md_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(svg, encoding="utf-8", newline="\n")
        print(f"  {slug}: {motif}")
    print(f"\nGenerated {len(posts)} thumbnails in {OUTPUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
