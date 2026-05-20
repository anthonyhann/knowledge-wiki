<div align="center">

# 📚 knowledge-wiki

**Full-lifecycle team knowledge management — capture, query, and maintain with zero friction.**

[![Version](https://img.shields.io/badge/version-0.6.0-blue.svg)](./CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Claude Skill](https://img.shields.io/badge/claude-skill-orange.svg)](./SKILL.md)
[![Requires](https://img.shields.io/badge/requires-ripgrep%20%7C%20git-lightgrey.svg)](#tool-dependencies)

Turns scattered content from Feishu, Apipost, code, and meetings into a structured, searchable, strictly-sourced local knowledge base — integrated directly into your Claude Code workflow.

[Quick Start](#quick-start) · [Commands](#commands) · [Templates](#template-library) · [Design](#design-principles) · [Changelog](./CHANGELOG.md)

</div>

---

## Why knowledge-wiki?

Most teams suffer from the same three problems:

| Problem | What happens | How this fixes it |
|---------|-------------|------------------|
| **Scattered knowledge** | Docs live in Feishu, Notion, Slack, and heads | Single `.knowledge/` directory, one ingestion command |
| **Knowledge rot** | Outdated docs silently mislead | 90-day expiry + git hook warnings before every push |
| **High entry barrier** | Nobody writes docs because templates are intimidating | Type-inferred scaffolding — just paste, AI structures it |

---

## Quick Start

```bash
# 1. Go to your project root
cd ~/your-project

# 2. Initialize (checks tools, creates .knowledge/, installs git hooks)
/knowledge-wiki init

# 3. Record your first piece of knowledge
/knowledge-wiki in "Print service timeout threshold is 30s, falls back to local cache"

# 4. Query it
/knowledge-wiki ask "print service timeout"

# 5. Run a health check anytime
/knowledge-wiki health
```

> [!TIP]
> `/knowledge-wiki init` auto-detects missing tools and offers one-command install. See [Tool Dependencies](#tool-dependencies).

---

## Commands

### Overview

| Command | What it does |
|---------|-------------|
| [`init`](#init) | Check tools · create `.knowledge/` · install git hooks |
| [`in`](#ingestion) | Ingest text, URLs, files, or code with zero friction |
| [`ask`](#query) | Strict-source Q&A — never guesses without a record |
| [`health`](#health) | Detect rot · scan external sources · coverage report |

### `init`

```bash
/knowledge-wiki init
```

Runs `check-deps.sh`, creates the directory structure, and installs two git hooks. Aborts if required tools (`rg`, `git`) are missing — choose auto-install, manual install, or abort.

### Ingestion

```bash
/knowledge-wiki in <text|URL|file-path>     # Smart ingest from any source
/knowledge-wiki in --update <slug>           # Update an existing entry

/knowledge-wiki in source add <url> [--name <label>]   # Register external source
/knowledge-wiki in source list
/knowledge-wiki in source remove <id>
```

### Query

```bash
/knowledge-wiki ask "<question>"             # Strict-source answer
/knowledge-wiki ask links <slug>             # Who references this doc?
/knowledge-wiki ask refs <slug>              # What does this doc reference?
```

### Health

```bash
/knowledge-wiki health                       # Full health report
/knowledge-wiki health rot                   # Expired / expiring docs
/knowledge-wiki health scan                  # External source change detection
/knowledge-wiki health coverage              # Coverage gaps
/knowledge-wiki health audit <slug>          # Confirm valid → promote to active
/knowledge-wiki health deprecate <slug>      # Mark as deprecated
```

---

## Directory Structure

After `init`, your project gets:

```
.knowledge/
├── README.md               ← Dual-audience entry (AI instructions on top, human guide below)
├── CLAUDE.md               ← AI collaboration contract + prohibited behaviors
├── AGENTS.md               ← AI navigation map (≤50 lines)
├── .sources.yaml           ← External source registry
│
├── glossary/               ← Term anchors — write here first, reference everywhere else
├── design/                 ← Architecture · solutions · ADRs (distinguished by `type`)
├── requirements/           ← PRDs, user stories, acceptance criteria
├── flows/                  ← Core business process flows
├── apis/                   ← Interface contracts, field mappings
├── data/                   ← Data models, DDL, storage docs
├── ops/                    ← Runbooks, alerts, traffic protection
├── incidents/              ← Post-mortems
├── bizrules/               ← Business rules shared across ops and engineering
├── meetings/               ← Meeting notes
└── people/{user-id}/       ← Personal context (AI read-only)
```

The `design/` directory uses a `type` frontmatter field to distinguish three subtypes:

| `type` | Use case |
|--------|---------|
| `architecture` | Living system architecture doc, continuously updated |
| `solution` | Technical design snapshot for a specific requirement |
| `adr` | Architecture Decision Record — captures the *why* |

<details>
<summary>Full directory spec and root file templates →</summary>

See [`references/directory-structure.md`](references/directory-structure.md) for the complete directory tree, per-directory responsibilities, and starter templates for `README.md`, `CLAUDE.md`, `AGENTS.md`, and `.sources.yaml`.

</details>

---

## Template Library

> [!NOTE]
> New in **v0.6.0** — each of the 12 knowledge types now has a dedicated body scaffold, enforced at ingestion time.

Instead of a generic TL;DR + details format, every type gets purpose-built structure:

| Template | Level | Contents |
|----------|-------|---------|
| `glossary.md` | L1 | Term · synonyms · field mappings · boundaries |
| `architecture.md` | L1 | Service topology · module responsibilities · dependencies |
| `adr.md` | L1 | Alternatives · tradeoffs · consequences |
| `requirement.md` | L1 | User stories · acceptance criteria |
| `solution.md` | L2 | Background · detailed design · impact |
| `flow.md` | L2 | Trigger · main flow · exception branches |
| `incident.md` | L2 | Timeline · 5 Whys · action items with owners |
| `bizrule.md` | L2 | Conditions · formulas · change history |
| `api.md` | L3 | Request · response · error codes |
| `data.md` | L3 | DDL · fields · indexes |
| `ops.md` | L3 | Timeouts · alerts · rate limits |
| `meeting.md` | — | Discussion points · conclusions · action items |

The ingestion flow runs **two new checkpoints**:

- **Step 2.5 — Template loading**: AI reads `_registry.yaml`, locates the matching scaffold, and structures the body before writing.
- **Step 8.5 — Quality gate**: Validates all `required_sections` and runs `quality_gate` checks. Blocks and returns a missing-items list if any section fails.

**Example quality gates:**

| Type | Gate |
|------|------|
| `glossary` | Must include ≥1 technical field name mapping (backend / DB / frontend) |
| `incident` | Each action item needs an owner + deadline; root cause must go beyond surface symptoms |
| `api` | All request/response fields must include types; ≥1 error code required |
| `bizrule` | Logic must be implementable in code — concrete formula or decision branches required |

<details>
<summary>Full registry and gate specs →</summary>

See [`references/templates/_registry.yaml`](references/templates/_registry.yaml) for all type definitions and gate rules.

Design rationale and comparison with GSD Artifact Taxonomy: [`DESIGN.md`](./DESIGN.md) — Section IX.

</details>

---

## Document Format

Every knowledge entry uses YAML frontmatter:

```yaml
---
title: Print Service Timeout Mechanism
type: ops
tags: [print, timeout, fallback]
owner: "@hanqiang"
created: 2026-05-12
expires: 2026-08-12        # Default: 90 days from creation. Use "never" for permanent docs.
status: draft              # draft | active | deprecated | canonical
sources:
  - "Manual entry @hanqiang 2026-05-12"
related:
  - "[[print-service-overview]]"
---
```

**Status lifecycle:**

```
draft ──(health audit)──▶ active ──(health deprecate)──▶ deprecated
                                ╲
                                 ──(manual promotion)──▶ canonical
```

| Status | Meaning | AI behavior |
|--------|---------|-------------|
| `draft` | Unconfirmed | Can reference; not a decision basis |
| `active` | Confirmed valid | Normal retrieval and citation |
| `deprecated` | No longer valid | Must not be cited |
| `canonical` | Authoritative and locked | Highest priority; AI must not modify |

---

## Git Hooks

`/knowledge-wiki init` installs two hooks automatically:

### `pre-push` — blocking

Runs before every `git push`. Checks for:

- Knowledge docs expiring within **7 days** or already expired
- External sources in `.sources.yaml` not synced for **>30 days**

If issues are found:

```
[1] Handle now   [2] Skip   [3] Abort push
```

> [!IMPORTANT]
> The hook is **completely silent when there are no issues** — it will never slow down a clean push.

### `commit-msg` — advisory

Triggers when your commit message contains `[kb]`:

```bash
git commit -m "fix: resolve print timeout not resetting [kb]"
# → Hint: ops/print-timeout.md exists in knowledge base — consider updating it
```

Does not block the commit. Output is advisory only.

---

## External Sources

Register external docs you want to track for changes in `.knowledge/.sources.yaml`:

```yaml
sources:
  - id: print-api-doc
    name: Print API Docs
    url: https://docs.apipost.net/docs/detail/xxx
    tracked_by: "@hanqiang"
    last_hash: ""
    last_synced: ""
    status: active          # active | stale | error
    related_docs:
      - apis/print-api.md
```

`/knowledge-wiki health scan` fetches each registered URL, computes a content hash, and notifies you on changes — **without auto-overwriting** your local docs.

---

## Tool Dependencies

`/knowledge-wiki init` auto-checks dependencies before creating any files.

### Group A — Required

| Tool | Required | Purpose |
|------|:--------:|---------|
| `rg` (ripgrep) | ✅ | Full-text search and backlink tracing |
| `git` | ✅ | Hook installation |
| `jq` | optional | Frontmatter parsing in hook scripts |

### Group B — Browser Automation (for URL ingestion)

> [!NOTE]
> All optional. Any single tool from this group enables URL ingestion.

| Tool | Best for |
|------|---------|
| `agent-browser` | General AI-native use (preferred default) |
| `browser-harness` | Dynamic pages with unstable selectors |
| `playwright` | Fixed-flow batch ingestion pipelines |
| `browser-use` | Multi-step LLM autonomous decisions |
| `page-agent` | Chinese-language websites |

```bash
bash references/scripts/check-deps.sh                    # Check only
bash references/scripts/check-deps.sh --install          # Install missing Group A tools
bash references/scripts/check-deps.sh --install-browser  # Install all Group B tools
```

Auto-selects the right package manager: `brew` · `apt` · `yum` · `npm` · `pipx`.

---

## Design Principles

1. **No source, no write, no answer** — `sources` is required on every entry; `ask` says "not found" rather than guessing.
2. **Single term definition** — Definitions live in `glossary/`; all other docs reference via `[[slug]]`.
3. **Draft-first** — New entries default to `status: draft`; human promotion required via `health audit`.
4. **Zero-index tracing** — Backlinks and forward refs scan Markdown directly with `rg`; no index files to maintain.
5. **Silent on pass** — Hooks and `health rot` produce no output when everything is clean.
6. **Deprecate must resolve references** — `health deprecate` uses `rg` to find all references before marking deprecated; prevents dangling links.
7. **Tool gate on init** — `init` aborts if required tools are missing; no partial state.
8. **Template as contract** *(v0.6.0)* — Ingestion body must follow `templates/{type}.md` scaffold exactly; AI cannot add/remove top-level headings; Step 8.5 gate enforces required sections.

---

## Usage Examples

<details>
<summary>Ingestion examples</summary>

```bash
# From a Feishu doc
/knowledge-wiki in https://xxx.feishu.cn/docx/xxx

# From a Feishu wiki page
/knowledge-wiki in https://xxx.feishu.cn/wiki/xxx

# Free-text entry
/knowledge-wiki in "Print service timeout is 30s; falls back to local cache on timeout"

# Extract design knowledge from source code
/knowledge-wiki in ./src/print/service.go

# Register an external source for ongoing tracking
/knowledge-wiki in source add https://docs.apipost.net/docs/detail/xxx --name "Print API Docs"
```

</details>

<details>
<summary>Query and tracing examples</summary>

```bash
# Ask a question — answer always cites source docs
/knowledge-wiki ask "What is the print service timeout?"

# Who links to this doc?
/knowledge-wiki ask links print-timeout

# What does this doc link to?
/knowledge-wiki ask refs print-timeout
```

</details>

<details>
<summary>Maintenance examples</summary>

```bash
# Check for external source updates
/knowledge-wiki health scan

# List expired or expiring docs
/knowledge-wiki health rot

# Confirm a doc is still valid (resets expiry +90 days)
/knowledge-wiki health audit print-timeout

# Deprecate an outdated doc (resolves all references first)
/knowledge-wiki health deprecate old-print-config
```

</details>

---

## Resource Index

| File | Purpose |
|------|---------|
| [`SKILL.md`](./SKILL.md) | Skill entry — tool tables, subcommand scaffold, AI invocation rules |
| [`DESIGN.md`](./DESIGN.md) | Architecture rationale, layering model, template library design |
| [`references/directory-structure.md`](references/directory-structure.md) | `.knowledge/` tree + root file templates |
| [`references/ingestion-rules.md`](references/ingestion-rules.md) | 11-step ingestion flow, slug rules, quality gates |
| [`references/ask-rules.md`](references/ask-rules.md) | Two-layer retrieval, answer format, expiry, links/refs |
| [`references/health-rules.md`](references/health-rules.md) | rot · scan · coverage · audit · deprecate specs |
| [`references/url-handling.md`](references/url-handling.md) | URL routing rules, Feishu subflow, scan routing |
| [`references/templates/_registry.yaml`](references/templates/_registry.yaml) | Central type → template + required sections + gates |
| [`references/scripts/check-deps.sh`](references/scripts/check-deps.sh) | Dependency checker + installer |

---

## Changelog

See [`CHANGELOG.md`](./CHANGELOG.md) for full version history.

---

<div align="center">

Built for teams that want their knowledge to stay alive, not just archived.

</div>
