<h1 align="center">📚 knowledge-wiki</h1>

<p align="center">
  <strong>Turn scattered docs into a structured, searchable, Agent-reasonable knowledge base</strong>
</p>

<p align="center">
  <a href="./README_zh.md">中文文档</a> ·
  <a href="./CHANGELOG.md">Changelog</a> ·
  <a href="./SKILL.md">Skill Spec</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/trigger-%2Fknowledge--wiki-blue" alt="trigger" />
  <img src="https://img.shields.io/badge/formats-11%2B-green" alt="formats" />
  <img src="https://img.shields.io/badge/platforms-Xuecheng%20%7C%20Lark%20%7C%20Apipost-orange" alt="platforms" />
  <img src="https://img.shields.io/badge/retrieval-BM25%20%2B%20Dense%20%2B%20GraphRAG-purple" alt="retrieval" />
</p>

---

## Why knowledge-wiki?

Your team's knowledge is scattered across Xuecheng docs, Lark spreadsheets, Apipost specs, code comments, and meeting notes. Every time someone asks *"How does this API work?"* or *"Why did we make that decision?"*, you either dig through half a dozen tools or ask a colleague who might not remember.

**knowledge-wiki unifies all that into one structured knowledge base** that AI Agents can directly search, reason over, and answer from.

| Problem | How we solve it |
|---------|-----------------|
| 🔍 **Can't find it** — docs live on 5+ platforms | Single knowledge base with hybrid search (BM25 + Dense + GraphRAG) |
| 🕰️ **It's outdated** — Xuecheng updated, local copy didn't sync | Persistent sync sources with auto-change detection |
| 🧠 **Knowledge rots** — code changes, nobody updates docs | Pre-push hook auto-detects stale docs and suggests updates |

---

## ✨ Core Capabilities

| Capability | What it does | Command |
|------------|-------------|---------|
| **RAG Q&A** | Instant answers from your knowledge base | `/knowledge-wiki ask` |
| **Agent Reasoning** | Multi-step ReACT reasoning for complex questions | `/knowledge-wiki reason` |
| **Wiki Generation** | Auto-generate structured, interlinked Wiki pages | `/knowledge-wiki wiki` |
| **Sync Sources** | Track external docs; auto-detect changes on push | `/knowledge-wiki source` |

---

## 🚀 Quick Start

### 1. Initialize

```bash
/knowledge-wiki init
# ✓ Creates .knowledge/ directory structure (7 sub-dirs under docs/)
# ✓ Generates governance files (CLAUDE.md / AGENTS.md / CONTRIBUTING.md)
# ✓ Installs 5 scripts (kb-sync.sh, generate-dashboard.py, etc.)
# ✓ Installs .git/hooks/pre-push (auto-check before push)
# ✓ Runs initial generation and health check
```

### 2. Import Documents

```bash
# From Xuecheng (requires Meituam intranet login)
/knowledge-wiki ingest https://km.sankuai.com/collabpage/2760577321

# From Lark (requires Lark login)
/knowledge-wiki ingest https://bytedance.larkoffice.com/docx/PW6PdvVPFoNwgjxgRPWcwBrknmc

# From Apipost — recursive, no login needed
/knowledge-wiki ingest "https://docs.apipost.net/docs/detail/5347b5d25884000" --recursive

# From local code
/knowledge-wiki ingest ./src/ --type code

# From a PDF
/knowledge-wiki ingest ./docs/technical-spec.pdf
```

### 3. Register Sync Sources

```bash
/knowledge-wiki source add https://km.sankuai.com/collabpage/2760577321 \
  --name "AI-DLC Framework" --tags "ai,framework"

/knowledge-wiki source list
# ID       Name                    Status   Last Synced
# src-001  AI-DLC Framework        active   2026-05-07
```

### 4. Use It

```bash
# Quick Q&A
/knowledge-wiki ask "What are the rate-limiting strategies for the API gateway?"

# Complex reasoning (auto-orchestrates KB + MCP tools + web search)
/knowledge-wiki reason "Analyze the root cause of rate-limit false positives based on historical ADRs"

# Visualize knowledge graph (open in browser)
/knowledge-wiki graph
```

---

## 📖 Usage Examples

### Onboarding a New Team Member

```bash
/knowledge-wiki ask "What's the difference between channel-side and delivery-side APIs?"

# Output:
# Channel APIs (/channel/) handle merchant-side messages, routed by Tag field...
# Delivery APIs (/delivery/) handle delivery status push, routed by Command field...
# Sources: [[api-gateway]] [[myt-adapter-architecture]] (relevance ⭐⭐⭐⭐)
# Confidence: high
#
# 💡 Related questions:
# 1. What is the complete flow for channel onboarding?
# 2. How do send and receive services differ in log format?
```

### Pre-Push Auto-Reminder

```bash
$ git push origin feature/rate-limiter

━━━ Knowledge Base Sync Analysis (.knowledge/) ━━━
📦 Changed files:
  internal/gateway/rate_limiter.go
  internal/gateway/config.go

📝 Suggested KB updates:
  pages/entities/api-gateway.md  [exists, needs update]

How to proceed?
  [1] Sync sources  [2] Update docs  [3] Both  [4] Skip & push
```

### Complex Multi-Step Reasoning

```bash
/knowledge-wiki reason \
  "The doudian channel frequently returns 5xx during peak hours. Analyze root cause based on current architecture and historical ADRs."

# Agent automatically:
# Thought: Need to understand current architecture and past decisions
# Action: kb_search("doudian 5xx rate limiting")
# Observation: Found pages/entities/doudian-adapter.md, docs/implementation/rate-limiter-v2-adr.md
# Thought: Check specific interface implementation
# Action: kb_read("doudian-adapter")
# ...
# Final Answer: Troubleshooting steps: 1. Confirm send vs receive side → 2. Check Tag routing config...
```

---

## 🗂 Directory Structure

```
.knowledge/
├── CLAUDE.md              # AI collaboration contract (Agent reads this first)
├── AGENTS.md              # AI navigation map (≤100 lines)
├── dashboard.md           # [CI-generated] Knowledge base dashboard
├── graph.html             # [CI-generated] Knowledge graph visualization
├── strategy/              # Team golden principles (low-frequency, owner-maintained)
├── docs/                  # Project docs (organized by lifecycle)
│   ├── requirements/      # PRDs, requirement docs, UI designs
│   ├── design/            # Tech specs, flowcharts, PUML
│   ├── implementation/    # ADRs, interface contracts
│   ├── quality/           # Test plans, acceptance docs
│   ├── release/           # Release notes, rollback plans
│   ├── exec-plans/        # Execution plans (active/completed)
│   ├── domain/            # Business domain knowledge
│   └── generated/         # [CI-generated] db-schema, api-changelog
├── people/{user-id}/      # Personal context (AI read-only)
├── playbooks/             # Locked task contracts (canonical, AI cannot modify)
├── pages/                 # Wiki main pages (AI auto-generated)
└── inbox/                 # Draft pages pending review
```

---

## 📋 All Commands

```
/knowledge-wiki init [path]               # Initialize KB (3 phases: create → install → execute)
/knowledge-wiki ingest <source>           # Import docs (11+ formats + Xuecheng/Lark/Apipost)
/knowledge-wiki ask "<question>"          # RAG Q&A (BM25 + Dense + GraphRAG + parent-child chunks)
/knowledge-wiki reason "<complex-q>"      # ReACT reasoning (auto-orchestrates tools & search)
/knowledge-wiki wiki [--enable|--disable] # Wiki mode toggle & auto-generate/update pages
/knowledge-wiki graph [path]              # Generate local knowledge graph HTML (zero deps)
/knowledge-wiki search <query>            # Hybrid search (raw results, no answer generated)
/knowledge-wiki lint [path]               # Check broken links, orphan pages, missing frontmatter
/knowledge-wiki eval [path]               # E2E evaluation (recall, BLEU-4, ROUGE-L, hallucination)
/knowledge-wiki export <format>           # Export as jsonl / qa-pairs / graphrag
/knowledge-wiki status                    # KB health overview
/knowledge-wiki sync [base_ref]           # Pre-push change analysis (auto-called by hook)
/knowledge-wiki source add <url> [opts]   # Register persistent sync source
/knowledge-wiki source list               # List all sources (with status & last sync time)
/knowledge-wiki source sync [id]          # Incremental sync (hash diff, auto-skip unchanged)
/knowledge-wiki source remove <id>        # Remove source (keeps generated pages)
```

---

## 📄 Supported Document Formats

**Local files:** Markdown · PDF · Word (.docx) · TXT · Images (OCR) · CSV/Excel · PPT (.pptx) · JSON · Code directories · Conversation logs

**Online platforms:**

| Platform | Access | Features |
|----------|--------|----------|
| Xuecheng `km.sankuai.com` | Meituam intranet login | Full heading/table/code extraction |
| Lark `larkoffice.com` | Lark login | TOC tree + structured body extraction |
| Apipost `docs.apipost.net` | Public, no login | API params auto-converted to entity pages |
| Web pages `https://...` | Public | Body text extraction, nav noise removed |

---

## 🔬 Retrieval Architecture

Four-layer hybrid retrieval for `/knowledge-wiki ask`:

| Layer | Method | Purpose |
|-------|--------|---------|
| 1. BM25 | ripgrep full-text scan on `pages/` | Exact keyword matching |
| 2. Dense | `.kb-meta/chunks.jsonl` top-K | Semantic vector similarity |
| 3. GraphRAG | `graph.json` 1-hop neighbors | Related context enrichment |
| 4. Parent-child chunks | Child hit → supplement parent chunk | Prevents semantic truncation |

**Fusion ranking:** high backlink_count → canonical (highest priority) → deprecated (auto-demoted)

---

## 🧪 Evaluation

```bash
/knowledge-wiki eval

# Sample output:
# Retrieval   Recall Hit Rate: 0.87  Precision: 0.79
# Generation  BLEU-4: 0.43  ROUGE-L: 0.61  Hallucination: 4.8%
# End-to-end  P50: 1.2s  P95: 2.8s
```

---

## 🏗 Methodology

knowledge-wiki draws from established practices:

- **AI-DLC Framework** — directory layering, AGENTS.md convention, CI gates, generated/ isolation
- **Zettelkasten** — atomic notes + explicit link networks
- **GraphRAG (Microsoft)** — community detection + graph summaries + hierarchical retrieval
- **ReACT Framework** — Thought-Action-Observation progressive reasoning loop
- **Obsidian WikiLinks** — bidirectional links and backlink tracking
- **RAG Best Practices** — semantic chunking + parent-child chunks + BM25/Dense hybrid

See [`references/methodology.md`](./references/methodology.md) for details.

---

## 📐 Project Structure

This skill uses progressive disclosure — `SKILL.md` is the navigation entry with command summaries; details live in on-demand `references/`:

| File | Content | When to read |
|------|---------|-------------|
| `references/kb-structure.md` | KB directory structure details | During init or restructuring |
| `references/doc-standards.md` | Frontmatter / WikiLink / chunking rules | Before ingest or wiki writes |
| `references/retrieval-config.md` | Retrieval parameter details (threshold/top_k/mode) | When tuning recall quality |
| `references/agents-claude-spec.md` | AGENTS.md / CLAUDE.md template spec | When generating governance files |
| `references/methodology.md` | 6 methodology sources in depth | Understanding design philosophy |
| `references/ingest-pipeline.md` | Agent processing flow + error handling | During ingest execution |
| `references/output-templates.md` | Output format examples for each command | When you need format examples |
| `references/data-schemas.md` | graph.json / sources.json / eval dataset schemas | When reading/writing metadata |
| `references/lint-rules.md` | Lint rule auto-fix suggestions | When lint reports errors |
| `references/scripts/` | 5 script templates (copied during init) | During init phase |

---

## 📜 License

Internal tool — Meituam Maiyatian Team
