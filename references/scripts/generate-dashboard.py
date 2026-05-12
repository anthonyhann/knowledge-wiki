#!/usr/bin/env python3
# generate-dashboard.py — 从 .kb-meta/stats.json 生成 dashboard.md
# 由 pre-push hook 自动调用，勿手动编辑 dashboard.md

import json, os, datetime
from pathlib import Path

KB_DIR = Path(".knowledge")
STATS_FILE = KB_DIR / ".kb-meta/stats.json"
SOURCES_FILE = KB_DIR / ".kb-meta/sources.json"
EVAL_FILE = KB_DIR / ".kb-meta/eval-results.json"
OUTPUT = KB_DIR / "dashboard.md"

def load_json(path, default=None):
    try:
        return json.loads(path.read_text()) if path.exists() else (default or {})
    except Exception:
        return default or {}

stats   = load_json(STATS_FILE)
sources = load_json(SOURCES_FILE, {"sources": []})
evals   = load_json(EVAL_FILE)

total   = stats.get("total_pages", 0)
active  = stats.get("active", 0)
draft   = stats.get("draft", 0)
deprecated = stats.get("deprecated", 0)
broken_links = stats.get("broken_links", 0)
orphans = stats.get("orphans", 0)
chunks  = stats.get("total_chunks", 0)

stale_sources = [s for s in sources.get("sources", []) if s.get("status") in ("stale", "error")]

recall  = evals.get("recall", "N/A")
bleu    = evals.get("bleu4", "N/A")
halluc  = evals.get("hallucination_rate", "N/A")

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

content = f"""---
generated: {now}
status: auto
---
<!-- 此文件由 generate-dashboard.py 自动生成，禁止手动编辑 -->

# 知识库看板

> 最后更新：{now}

## 📊 统计

| 指标 | 数值 |
|------|------|
| 总页面 | {total}（active: {active} | draft: {draft} | deprecated: {deprecated}） |
| RAG chunks | {chunks} |
| 断链 | {broken_links} |
| 孤立页面 | {orphans} |

## 🔗 同步源状态

| 状态 | 数量 |
|------|------|
| active | {len([s for s in sources.get('sources',[]) if s.get('status')=='active'])} |
| stale / error | {len(stale_sources)} |

{"⚠️ **有未同步的源，建议运行 `/knowledge-wiki source sync`**" if stale_sources else "✅ 所有同步源正常"}

## 📈 最新评测

| 指标 | 数值 |
|------|------|
| 召回命中率 | {recall} |
| BLEU-4 | {bleu} |
| 幻觉率 | {halluc} |
"""

OUTPUT.write_text(content)
print(f"✓ dashboard.md 已更新：{OUTPUT}")
