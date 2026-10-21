<div align="center">

# 🧠 knowledge-wiki

### A governed knowledge-graph skill for AI coding agents

Team knowledge, **compiled** — not just stored. 12 typed templates · 14-step ingestion pipeline · 4-layer retrieval · 3-tier edge trust model. Every answer cites its source, or honestly says "no record".

[![version](https://img.shields.io/badge/version-v2.1.0-blue?style=flat-square)](CHANGELOG.md)
[![license](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![agents](https://img.shields.io/badge/agents-Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20Cursor-purple?style=flat-square)](#-quickstart)
[![install](https://img.shields.io/badge/install-npx%20skills%20add-black?style=flat-square)](#-quickstart)
[![stars](https://img.shields.io/github/stars/anthonyhann/knowledge-wiki?style=flat-square)](https://github.com/anthonyhann/knowledge-wiki/stargazers)

[Quickstart](#-quickstart) · [What it does](#-what-it-does) · [Triggers](#-trigger-phrases) · [Layout](#-repository-layout) · [When NOT to use](#-when-not-to-use-it) · [CHANGELOG](CHANGELOG.md) · [中文版](README_zh.md)

</div>

## Your AI agent, probably

- Answers from **model memory** instead of your team's actual decisions — confidently wrong
- Forgot yesterday's postmortem while writing today's code
- Can *find a doc*, but can't tell you **"what breaks if I change X"**
- Meanwhile your wiki rots silently — nobody knows which doc is stale

This skill fixes that with one mechanism: **documents are the single source of truth, and the knowledge graph is a pure function of them** (`graph = compile(documents)`). Delete `.knowledge/.graph/` and you're back to a plain doc library — the graph is layered on, never baked in.

## What an answer looks like

```
$ /knowledge-wiki ask "what's the print-service timeout?"

回答：打印服务超时阈值为 30s，超时后 fallback 到本地缓存，不直接报错。
来源：.knowledge/ops/print-timeout.md（第 12 行）
录入：@alice，2026-05-12
状态：FRESH（距过期还有 82 天）
被引用：[[order-flow-design]]（1 处）
```

No record? It says so — and refuses to fill the gap with training data (invariant C1).

## 🚀 Quickstart

**For humans** — 3 steps:

```bash
# 1. Install the skill
npx skills add anthonyhann/knowledge-wiki

# 2. Then, in your AI coding agent (Claude Code / Codex / Cursor …), run:
/knowledge-wiki init

# 3. Record your first piece of knowledge
/knowledge-wiki in The print service times out at 30s, then falls back to local cache
```

`init` checks dependencies (`rg`/`git`), creates the `.knowledge/` skeleton (10 business dirs + index/log/queue system dirs), and installs 5 git hooks.

**For AI agents** — paste this to your agent:

> Install the knowledge-wiki skill from https://github.com/anthonyhann/knowledge-wiki (e.g. `git clone` it into my skills directory, or `npx skills add anthonyhann/knowledge-wiki`), then read its SKILL.md and run `/knowledge-wiki init` in my project.

## ✨ What it does

| Scenario | You say | It does |
|---|---|---|
| Ingest anything | `in <text / URL / file / code>` | 14-step pipeline: type inference → per-type template → quality gate → index → backlink queue → audit log |
| Ask with receipts | `ask "<question>"` | 4-layer retrieval (index pre-filter → ripgrep → fuzzy → semantic); 5-element answer with source/owner/freshness/ref-chain |
| Ask **relationships** | `ask graph "X"` · `ask explain "X"` · `ask path "A" "B"` | Neighborhood subgraph, full node explanation, multi-hop knowledge chain — authoritative edges only, inferred edges labeled ⚠️ |
| QA knowledge packs | `ask test "<module>"` | Aggregates test env/rules/checklists/pitfalls/test-data into one package for QA agents |
| Code → docs | `docs --staged` | Analyzes your diff, asks **one suggestion at a time**, never blocks the commit |
| Keep it alive | `health` / `rot` / `scan` / `lint` / `distill` | Expiry scans, external-source drift detection, 14 consistency checks, dedup & orphan detection |
| See the whole web | `health graph-build` → `graph export --html` | Compiles docs → `graph.json`; exports interactive HTML / Obsidian Canvas / GraphML |
| Trust governance | `health discover` → `health edge-review` | AI-proposed edges queue up for **human review**; approved edges are written back into docs, then re-derived. No auto-approve backdoor |

## 🗣️ Trigger phrases

The skill activates when you say things like:

| When you say… | It runs |
|---|---|
| "record this to the knowledge base" / "把这个记到知识库" | `in` |
| "does the knowledge base have…?" / "查一下" | `ask` |
| "how are X and Y connected?" / "what breaks if I change X?" | `ask graph` / `ask path` |
| "knowledge base health check" | `health` |
| "document this commit" | `docs` |

## 📊 Why trust it

Numbers you can verify in this repo:

- **12 typed templates** with per-type required sections + quality gates — no one-size-fits-all "TL;DR + details"
- **14 rule documents** in [`references/`](references/) covering ingestion, retrieval, lint, graph, trust, logs
- **12 scripts**: 6 PEP 723 graph engines (single dependency `networkx`, uv-isolated) + 5 git hooks + 1 dependency checker
- **14 consistency checks** (L1–L9 + 5 graph/pending-queue lints) run centrally, never blocking your flow
- **8 core invariants (C1–C8)** + **9 soft behaviors (E1–E9)** — e.g. C1: no source, no write, no answer
- **3-tier edge trust model** (EXTRACTED / INFERRED / AMBIGUOUS) with a human-review gate; AMBIGUOUS edges can never become hard conclusions
- Shipped in **9 gated phases** (v0.1.0 → v2.1.0), each with a documented acceptance matrix — see [CHANGELOG.md](CHANGELOG.md)

## 📈 Battle-tested in production

This is not a weekend demo. Between **2026-04 and 2026-10** it ran inside a production fleet of **49 agent skills** tracked over **342 scored optimization records** (measured by [skill-eval-optimizer](https://github.com/anthonyhann/skill-eval-optimizer)):

- **67.8 → 90.3 / 100** across **34 optimization rounds** — every round scored on the same 8-dimension rubric, a change kept only when the score actually moved up
- One round *shrank* the skill **404 → 216 lines (35 KB → 21.4 KB, −39% tokens)** while *raising* the score — smaller context, better behavior
- Fleet-wide: of 44 skills with full baselines, **40 improved, average +9.9 points** — this repo is what survived that loop

## 📂 Repository layout

```
knowledge-wiki/
├── SKILL.md                  # Entry: command skeleton + C1–C8 invariants + E1–E9 soft behaviors
├── DESIGN.md                 # L1/L2/L3 cognitive-layer architecture + template-library rationale
├── CHANGELOG.md              # Full version history (v0.1.0 → v2.1.0)
├── TODO.md                   # Roadmap & design-decision memos
├── test-prompts.json         # Dry-run eval prompts (7 cases: happy + edge)
└── references/               # Lazy-loaded authority docs (loaded on demand, never up-front)
    ├── *.md                  # 14 rule docs: ingestion / ask / index / backlink / log / lint /
    │                         #   health / docs / url / graph-model / graph-build / trust / pending-edges
    ├── templates/            # 12 type templates + registry + 5 system config templates
    └── scripts/              # 6 graph engines (Python, PEP 723) + 5 git hooks + check-deps.sh
```

What `init` creates in *your* project: `.knowledge/` with 10 business directories (`glossary/ design/ requirements/ flows/ case/ tests/ apis/ db/ ops/ synthesis/`) organized by the L1 domain / L2 execution / L3 capability layering — see [DESIGN.md](DESIGN.md).

## ⚠️ When NOT to use it

Honest boundaries — this skill is **not for**:

- **Personal notes / diaries / chat logs / throwaway drafts** — it's built for team knowledge tied to a codebase
- **Teams wanting a hosted, real-time-collaboration wiki** — this is local Markdown + git; there is no server, no web UI, no multiplayer editing
- **Anyone unwilling to maintain `sources` / `status` discipline** — C1 means the agent *refuses to answer* when there's no record; that's the point, but it's a habit change
- **Huge corpora (10k+ docs) needing vector search** — retrieval is ripgrep + segmented indexes, deliberately embedding-free and inspectable

## 🙋 About

Built and dogfooded daily by [@anthonyhann](https://github.com/anthonyhann) on real engineering projects — every feature in the CHANGELOG exists because an actual workflow needed it. If it saves your team a re-derivation of "why did we do it this way?", a ⭐ tells the next team it works.

## License

MIT © [anthonyhann](https://github.com/anthonyhann) — see [LICENSE](LICENSE).
