# 数据结构规范

## graph.json

```json
{
  "nodes": [{ "id": "slug", "label": "名称", "type": "entity", "tags": [], "status": "active", "backlink_count": 5, "tldr": "..." }],
  "links": [{ "source": "a", "target": "b", "relation": "depends_on" }],
  "meta": { "generated_at": "YYYY-MM-DD", "total_nodes": 0, "total_links": 0 }
}
```

## sources.json（持久化同步源）

```json
{
  "sources": [{
    "id": "src-001", "name": "别名", "url": "...",
    "type": "sankuai|feishu|apipost|web",
    "recursive": false, "tags": [],
    "added_at": "YYYY-MM-DD", "last_synced": "YYYY-MM-DD HH:MM",
    "last_hash": "sha256:...", "status": "active|stale|error|paused",
    "page_count": 3
  }]
}
```

**stale 判定：** `last_synced` 超过 7 天自动标记（可在 SCHEMA.md `source_stale_days` 调整）。

## 评测数据集（assets/eval/）

```jsonl
{"id": "q001", "question": "...", "expected_pages": ["slug1"], "expected_answer_keywords": ["关键词"]}
```
