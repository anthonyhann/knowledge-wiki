# knowledge-wiki

<div align="center">

**Knowledge Compiler** — Transform scattered, rotting knowledge into a structured, searchable, and strictly traceable local knowledge base.

[![Version](https://img.shields.io/badge/version-v1.1.0-blue.svg)](./CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Lang](https://img.shields.io/badge/lang-中文-red.svg)](./README_zh.md)

[中文文档](./README_zh.md) · [Design Doc](./DESIGN.md) · [Changelog](./CHANGELOG.md) · [TODO](./TODO.md)

</div>

---

## Why knowledge-wiki?

AI-assisted development suffers from a fundamental cognitive gap: codebases are documented as **flat text chunks**, and retrieval systems only optimize semantic similarity without distinguishing "decision intent" from "execution fact".

Specifically, AI agents cannot answer three questions:

- **Who owns this?** (Decision routing) — Which service should handle this requirement?
- **How to do it?** (Execution orchestration) — What's the standard process? What if it fails?
- **What tool to use?** (Atomic invocation) — What does the interface look like? What's the SLA?

> **Core conclusion**: The bottleneck is not retrieval precision, but **cognitive fidelity** — the ability to represent knowledge in layers, annotate health status, verify cross-layer reference integrity, and explicitly model "what the organization doesn't know."

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Concepts](#core-concepts)
- [L1 / L2 / L3 Three-Layer Architecture](#l1--l2--l3-three-layer-architecture)
- [Commands](#commands)
- [Tool Dependencies](#tool-dependencies)
- [Domain-Based Browser Routing](#domain-based-browser-routing)
- [Template Library](#template-library)
- [Document Lifecycle](#document-lifecycle)
- [Frontmatter Format](#frontmatter-format)
- [Git Hooks](#git-hooks)
- [Usage Examples](#usage-examples)
- [Design Principles](#design-principles)
- [Quick Start](#quick-start)
- [Resource Index](#resource-index)

---

## Architecture Overview

```
                ┌─────────────────────┐
User input ───►│   in  (14 steps)    │
                └──┬──────────────────┘
                   ├── .knowledge/{dir}/{slug}.md     (write)
                   ├── .index/{type}.idx.md           (Step 9.5 index update)
                   ├── .pending-backlinks.yaml        (Step 9.6 backlink enqueue)
                   └── .logs/personal/{id}.md         (Step 10 log)

                ┌─────────────────────┐
User query ───►│   ask  (3 layers)   │
                └──┬──────────────────┘
                   ├── Layer -1 : Index pre-filter
                   ├── Layer  0 : rg keyword match
                   ├── Layer 0.5: frontmatter fallback
                   ├── Layer  1 : semantic filtering → answer
                   └── .logs/personal/{id}.md         (log)

                ┌─────────────────────────────────────┐
                │              health                  │
                ├─────────────────────────────────────┤
                │ rot / scan / coverage (enhanced)     │
                │ lint          (L1–L9 consistency)    │
                │ backlink-consume  (queue flush)      │
                │ index-rebuild     (full rebuild)     │
                │ distill           (cognitive distill)│  ← v1.1.0
                │ audit / deprecate                    │
                │ └→ .logs/personal/{id}.md + digest   │
                └─────────────────────────────────────┘
```

---

## Core Concepts

> Evolved from "knowledge storage" to "**knowledge compilation**" — every operation not only stores knowledge but makes the entire knowledge network denser, more accurate, and more valuable.

| Capability | Description | Analogy |
|---|---|---|
| **Segmented Indexing** | 9 idx files by type; ask reads index first, then rg for precise search | "Search from scratch" → "Check the table of contents first" |
| **Operation Logging** | Per-person log files with hash-based privacy; cross-session context recovery | "No history" → "Know what was done recently" |
| **Bidirectional References** | Backlinks enqueued on ingest, batch-written by health; prevents one-way reference aging | "Only new docs know old docs" → "Old docs know they're referenced" |
| **Consistency Checking** | Centralized L1–L9 detection (contradictions / dangling refs / status mismatch); only during health | "Don't know there's a problem" → "Periodic health scan auto-discovers issues" |
| **Ask Backflow** | Synthesized analysis can be ingested as a `synthesis` document | "Q&A is ephemeral" → "Valuable discoveries can be persisted" |
| **Three-Layer Defense** `v0.9.0` | Index accuracy: AI real-time write + health rebuild eventual consistency + pre-commit hook interception | "Write and hope" → "Write → Fix → Intercept full coverage" |
| **Cognitive Distillation** `v1.1.0` | Jaccard dedup + low-quality draft cleanup + orphan detection | "Passive management" → "Proactive evolution" |

---

## L1 / L2 / L3 Three-Layer Architecture

| Layer | Alias | Cognitive Role | Core Question | Knowledge Objects |
|---|---|---|---|---|
| **L1 Domain** | Skeleton | Decision | Who owns this? What can/cannot be done? | Boundaries · Intent · State Machine · Collaboration Topology |
| **L2 Execution** | Molecule | SOP Orchestration | How to do it? What order? What if it fails? | Trigger Binding · Execution DAG · Branch Conditions · Human Nodes |
| **L3 Capability** | Atom | Tool Invocation | What tool? Interface spec? SLA? | Input Params · Output Structure · Protocol Coordinates |

| Directory | Type | Layer |
|---|---|---|
| `glossary/` | glossary | L1 — Core entity definitions, terminology anchor points |
| `design/` | architecture / adr | L1 — System architecture, ADRs |
| `requirements/` | requirement | L1 — PRDs, feature specs, acceptance criteria |
| `flows/` | flow | L2 — Business process SOPs, business rules |
| `case/` | case | L2 — Reverse examples, incident postmortems |
| `design/` | solution | L2 — Technical solution snapshots |
| `synthesis/` | synthesis | L2 — Ask backflow synthesis documents |
| `apis/` | api | L3 — Interface contracts, field mappings |
| `db/` | db | L3 — Data models, storage design |
| `ops/` | ops | L3 — Runbooks, alert thresholds |

> Full directory tree, type mapping, and L1/L2/L3 definitions are maintained in [`references/directory-structure.md`](./references/directory-structure.md) (single source of truth). Design philosophy is in [`DESIGN.md`](./DESIGN.md).

---

## Commands

```bash
# Initialize (with tool dependency check + 4 git hooks)
/knowledge-wiki init

# Ingest
/knowledge-wiki in <text/URL/file-path>
/knowledge-wiki in --update <slug>
/knowledge-wiki in source add <url> [--name <name>]
/knowledge-wiki in source list
/knowledge-wiki in source remove <id>
/knowledge-wiki in --from-answer "<brief description>"   # Ask backflow

# Query
/knowledge-wiki ask "<question>"
/knowledge-wiki ask links <slug>        # Reverse trace: who references this doc
/knowledge-wiki ask refs  <slug>        # Forward trace: what this doc references

# Maintenance
/knowledge-wiki health                  # Comprehensive report
/knowledge-wiki health --json           # JSON format output          [v0.9.0]
/knowledge-wiki health --verbose        # Detailed mode with ASCII charts [v0.9.0]
/knowledge-wiki health rot              # Scan expired/expiring documents
/knowledge-wiki health scan             # Detect external source changes
/knowledge-wiki health coverage         # Coverage + Q&A gap analysis
/knowledge-wiki health audit <slug>     # Confirm document valid, upgrade to active
/knowledge-wiki health deprecate <slug> # Mark document deprecated
/knowledge-wiki health lint             # Consistency check L1–L9
/knowledge-wiki health lint --fix       # Safe auto-fix (L3+L8)
/knowledge-wiki health backlink-consume # Consume backlink queue
/knowledge-wiki health index-rebuild    # Full rebuild of segmented indexes
/knowledge-wiki health distill          # Cognitive distillation preview [v1.1.0]
/knowledge-wiki health distill --execute # Execute distillation (user confirms each step)
```

---

## Tool Dependencies

`/knowledge-wiki init` calls `references/scripts/check-deps.sh` before creating directories.

### Group A — Core Tools (Required)

| Tool | Required | Purpose |
|---|---|---|
| `rg` (ripgrep) | **REQUIRED** | Keyword search / tracing |
| `git` | **REQUIRED** | Hook installation & triggering |
| `jq` | OPTIONAL | Hook script frontmatter parsing |

### Group B — Browser Automation (any one is sufficient)

| Tool | Description | Best For |
|---|---|---|
| `agent-browser` | Lightweight Swiss-army knife for AI tool calls | General AI-first usage |
| `browser-harness` | Self-healing browser hand for AI coding assistants | Dynamic pages, volatile selectors |
| `playwright` | Engineering-grade E2E testing foundation | Fixed-flow batch ingest/scan |
| `browser-use` | Full brain for LLM autonomous operation | Multi-step LLM decision-making |
| `page-agent` | Domain expert for Chinese web pages | Chinese-language sites |

> All Group B tools are OPTIONAL; any one installed can handle internal document URLs.

### One-Click Install

```bash
bash references/scripts/check-deps.sh                   # Check only
bash references/scripts/check-deps.sh --install         # Install missing core tools (Group A)
bash references/scripts/check-deps.sh --install-browser # Install missing browser tools (Group B)
```

The script auto-selects install commands based on OS (macOS → brew / Linux → apt|yum / npm / pipx).

---

## Domain-Based Browser Routing

Internal document URLs (Feishu, Apipost, etc.) are routed to browser automation tools by domain.

```
Domain                              Tool
──────────────────────────────────────────────────────────
feishu.cn / larkoffice.com      →   agent-browser / browser-harness / …
apipost.net                     →   agent-browser  (traverse directory tree)
other public URLs               →   any Group B tool
```

Full tool selection matrix: [`references/url-handling.md`](./references/url-handling.md).

---

## Template Library

Each of the **9 types** has a dedicated template skeleton (`synthesis` added in v0.8.0):

```
references/templates/
├── _registry.yaml      ← Central registry (type → template + required sections + quality gate)
├── glossary.md         ← L1  Term definition
├── architecture.md     ← L1  Architecture
├── adr.md              ← L1  Architecture decision record
├── requirement.md      ← L1  Requirement / PRD
├── flow.md             ← L2  Business process SOP
├── solution.md         ← L2  Technical solution
├── case.md             ← L2  Reverse example / incident
├── synthesis.md        ← L2  Synthesis (Ask backflow)  [v0.8.0]
├── api.md              ← L3  Interface contract
├── db.md               ← L3  Data model
└── ops.md              ← L3  Runbook
```

**Key pipeline steps** (15 steps total):

| Step | Name | Description |
|---|---|---|
| 2.5 | Template Loading | Load `_registry.yaml` → `templates/{type}.md`, structure content per skeleton |
| 2.65 | Similarity Detection `v1.1.0` | Jaccard quick match (>0.70 prompts user to consider `--update`). Non-blocking |
| 8.5 | Quality Gate | Validate `required_sections` completeness + run `quality_gate` text checks before write |
| 9.5 | Index Update | Update `.index/` idx file after successful write (non-blocking; WARNING on failure) |
| 9.6 | Backlink Enqueue | If `related ≥ 1` and target not deprecated and queue < 15, write to `.pending-backlinks.yaml` |
| 10 | Operation Log | All operations logged to `.logs/personal/{mis-id}.md` |

---

## Document Lifecycle

| Status | Meaning | AI Behavior |
|---|---|---|
| `draft` | Pending confirmation | May reference, not for decision-making |
| `active` | Officially valid | Normal retrieval & citation |
| `deprecated` | Obsolete | **Forbidden** to reference |
| `canonical` | Authoritative lock | Highest priority; AI must not modify |

Retrieval priority: `canonical > active > draft` (deprecated is excluded)

---

## Frontmatter Format

```yaml
---
title: Print Service Timeout Mechanism
type: ops
tags: [print, timeout, fallback]
owner: "@hanqiang"
created: 2026-05-12
expires: 2026-08-12        # Default 90 days; use "never" for long-term validity
status: draft              # draft | active | deprecated | canonical
sources:
  - "Manual entry @hanqiang 2026-05-12"
related:
  - "[[print-service-overview]]"
---
```

---

## Git Hooks

`/knowledge-wiki init` installs **4** git hooks:

| Hook | Trigger | Behavior |
|---|---|---|
| `pre-commit` `v0.9.0` | Staged `.knowledge/` files | Checks L2 dangling refs + L5 orphan indexes. ERROR blocks; WARNING does not |
| `post-merge` `v0.9.0` | After merge | >3 docs changed or rebuild >30 days ago → prompts `health index-rebuild`. Never auto-executes |
| `pre-push` | Before push | Detects expiring (≤7d) or expired docs + unsynced sources (>30d). Prompts `[1] Handle  [2] Skip  [3] Abort` |
| `commit-msg` | Commit with `[kb]` tag | Checks if related knowledge docs exist, suggests update or creation. Non-blocking |

---

## Usage Examples

```bash
# Ingest from Feishu (via browser automation)
/knowledge-wiki in https://xxx.feishu.cn/docx/xxx

# Manual text entry
/knowledge-wiki in "Print service timeout threshold is 30s, fallback to local cache"

# Ingest from code file
/knowledge-wiki in ./src/print/service.go

# Query the knowledge base
/knowledge-wiki ask "What is the print service timeout config?"

# Reverse trace: who references print-timeout
/knowledge-wiki ask links print-timeout

# Register external knowledge source (continuous change tracking)
/knowledge-wiki in source add https://docs.apipost.net/docs/detail/xxx --name "Print API Docs"

# Check external source updates
/knowledge-wiki health scan

# View expired documents
/knowledge-wiki health rot

# Confirm a document is still valid (reset expiry +90 days)
/knowledge-wiki health audit print-timeout
```

---

## Design Principles

1. **No source, no write, no answer** — `sources` is required; `ask` with no knowledge base match says so explicitly
2. **Unique terminology** — Term definitions anchored in `glossary/`; other docs use `[[slug]]` references
3. **Draft-first** — New ingests default to `status: draft`; upgraded via `health audit`
4. **Silent pass-through** — Hooks and rot scans produce no output when everything is fine
5. **Deprecate must handle references** — `rg` finds all references before deprecation; prevents dangling links
6. **Index-assisted retrieval** `v0.8.0` — `.index/` segmented indexes as Layer -1 pre-filter
7. **Operation traceability** `v0.8.0` — All operations logged; ask content is hash-redacted
8. **Deferred backwrite** `v0.8.0` — Backlinks queued in `.pending-backlinks.yaml` for batch consumption
9. **Centralized lint** `v0.8.0` — Contradiction detection only during `health lint`, never blocks in/ask
10. **Domain-based browser routing** — Internal document URLs routed to browser tools by domain
11. **Tool check gate** — `init` Step 0 must run `check-deps.sh`; missing required tools aborts init
12. **Template as contract** — Ingest content strictly follows `references/templates/{type}.md` skeleton
13. **No re-backflow** `v0.8.0` — `synthesis` docs cannot generate new synthesis (prevents nesting)
14. **Three-layer data defense** `v0.9.0` — AI real-time write + health rebuild + pre-commit hook interception
15. **Cognitive distillation** `v1.1.0` — `health distill` scans for duplicate/low-quality/orphan knowledge; preview by default
16. **Pre-ingest dedup** `v1.1.0` — Step 2.65 Jaccard quick match (>0.70 prompts); reduces knowledge duplication

---

## Quick Start

```bash
# 1. Navigate to project root
cd ~/your-project

# 2. Initialize (auto-checks tool dependencies)
/knowledge-wiki init
# Missing tools: [1] One-click install  [2] Manual install & retry  [3] Abort
# On pass: creates .knowledge/ directory + installs git hooks

# 3. Ingest first knowledge item
/knowledge-wiki in "Print service timeout threshold 30s"

# 4. Query to verify
/knowledge-wiki ask "print service timeout"

# 5. Periodic maintenance
/knowledge-wiki health
```

---

## Resource Index

| Path | Purpose |
|---|---|
| `SKILL.md` | Skill entry point — tool tables + command skeleton |
| `DESIGN.md` | L1/L2/L3 layered architecture + template library design |
| `TODO.md` | Pending capability list + version roadmap |
| `references/directory-structure.md` | `.knowledge/` complete directory framework + root file templates |
| `references/url-handling.md` | URL handling rules + domain routing + scan routing |
| `references/ingestion-rules.md` | AI structured ingest process (14 steps) |
| `references/index-rules.md` | Segmented index rules (three-layer data accuracy) |
| `references/log-rules.md` | Operation log rules (per-person files / archive / digest) |
| `references/backlink-rules.md` | Bidirectional backwrite rules (pending queue / deferred consumption) |
| `references/lint-rules.md` | Consistency check rules (L1–L9 / --fix safety boundary) |
| `references/templates/_registry.yaml` | Template registry (9 types) + required sections + quality gates |
| `references/templates/{type}.md` | 9 type-specific content skeleton templates |
| `references/templates/_meta.yaml.tpl` | Index metadata initialization template `v0.8.1` |
| `references/templates/_logs_config.yaml.tpl` | Log config initialization template `v0.8.1` |
| `references/templates/_pending_backlinks.yaml.tpl` | Empty queue initialization template `v0.8.1` |
| `references/templates/_idx_empty.md.tpl` | Generic idx header template `v0.8.1` |
| `references/ask-rules.md` | Three-layer retrieval + log recording + ask backflow prompt |
| `references/health-rules.md` | Comprehensive report + all health subcommands |
| `references/scripts/check-deps.sh` | Tool dependency check + one-click install |
| `references/scripts/pre-commit.sh` | git pre-commit hook `v0.9.0` |
| `references/scripts/post-merge.sh` | git post-merge hook `v0.9.0` |
| `references/scripts/pre-push.sh` | git pre-push hook |
| `references/scripts/commit-msg.sh` | git commit-msg hook |

Full changelog: [`CHANGELOG.md`](./CHANGELOG.md)

---

## License

[MIT](./LICENSE)
