#!/usr/bin/env bash
# knowledge-wiki pre-commit hook
# 轻量级 lint：仅检查 L2（悬空引用）+ L5（孤儿索引），目标 <2s 执行
# 安装：cp references/scripts/pre-commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -euo pipefail

KB_DIR=".knowledge"

# 仅在有 .knowledge/ 目录时执行
if [ ! -d "$KB_DIR" ]; then
  exit 0
fi

# 仅检查本次 commit 中涉及 .knowledge/ 的文件
STAGED_KB_FILES=$(git diff --cached --name-only --diff-filter=ACMR | grep "^\.knowledge/" || true)

if [ -z "$STAGED_KB_FILES" ]; then
  # 本次 commit 不涉及知识库文件，静默放行
  exit 0
fi

ERRORS=0
WARNINGS=0

# ─── L2 快速检查：staged 文件中的 related 引用是否存在 ───
for file in $STAGED_KB_FILES; do
  # 跳过系统目录文件
  if [[ "$file" == .knowledge/.index/* ]] || [[ "$file" == .knowledge/.logs/* ]] || [[ "$file" == .knowledge/.pending-backlinks* ]] || [[ "$file" == .knowledge/.sources* ]]; then
    continue
  fi

  # 跳过非 .md 文件
  if [[ "$file" != *.md ]]; then
    continue
  fi

  # 提取 related 中的 slug
  RELATED_SLUGS=$(git show ":$file" 2>/dev/null | grep -oP '\[\[\K[^\]]+' || true)

  for slug in $RELATED_SLUGS; do
    # 检查对应文件是否存在（在工作树中）
    FOUND=$(find "$KB_DIR" -name "${slug}.md" -not -path "*/.index/*" -not -path "*/.logs/*" 2>/dev/null | head -1)
    if [ -z "$FOUND" ]; then
      echo "⚠️  [pre-commit L2] 悬空引用: $file → [[$slug]]（文件不存在）"
      WARNINGS=$((WARNINGS + 1))
    fi
  done
done

# ─── L5 快速检查：idx 中的 slug 对应文件是否存在 ───
for idx_file in "$KB_DIR"/.index/*.idx.md; do
  if [ ! -f "$idx_file" ]; then
    continue
  fi

  # 提取 idx 表格中的 slug 列（第一列，跳过表头）
  IDX_SLUGS=$(tail -n +4 "$idx_file" | grep "^|" | awk -F'|' '{print $2}' | tr -d ' ' | grep -v "^$" | grep -v "^slug$" || true)

  for slug in $IDX_SLUGS; do
    FOUND=$(find "$KB_DIR" -name "${slug}.md" -not -path "*/.index/*" -not -path "*/.logs/*" 2>/dev/null | head -1)
    if [ -z "$FOUND" ]; then
      echo "❌ [pre-commit L5] 孤儿索引: $idx_file 引用 $slug 但文件不存在"
      ERRORS=$((ERRORS + 1))
    fi
  done
done

# ─── 结果 ───
if [ $ERRORS -gt 0 ]; then
  echo ""
  echo "🚫 pre-commit 检测到 $ERRORS 个 ERROR + $WARNINGS 个 WARNING"
  echo "   建议运行 /knowledge-wiki health lint 查看完整报告"
  echo "   使用 git commit --no-verify 跳过此检查"
  exit 1
fi

if [ $WARNINGS -gt 0 ]; then
  echo ""
  echo "⚠️  pre-commit 检测到 $WARNINGS 个 WARNING（不阻断提交）"
  echo "   建议运行 /knowledge-wiki health lint 查看详情"
fi

exit 0