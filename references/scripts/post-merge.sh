#!/usr/bin/env bash
# knowledge-wiki post-merge hook
# 合并后检查知识库变更，提示是否需要 index-rebuild
# 安装：cp references/scripts/post-merge.sh .git/hooks/post-merge && chmod +x .git/hooks/post-merge

set -uo pipefail

KB_DIR=".knowledge"

# 仅在有 .knowledge/ 目录时执行
if [ ! -d "$KB_DIR" ]; then
  exit 0
fi

# 检查本次 merge 中涉及 .knowledge/ 的文件变更数
# $1 = 1 表示 squash merge，否则为普通 merge
CHANGED_KB_FILES=$(git diff-tree -r --name-only --diff-filter=ACMR ORIG_HEAD HEAD 2>/dev/null | grep "^\.knowledge/" || true)
CHANGED_COUNT=$(echo "$CHANGED_KB_FILES" | grep -c "." 2>/dev/null || echo "0")

if [ "$CHANGED_COUNT" -eq 0 ]; then
  # 无知识库文件变更，静默退出
  exit 0
fi

# 检查是否有新的业务文档（非系统文件）
NEW_DOCS=$(echo "$CHANGED_KB_FILES" | grep -v "^\.knowledge/\.index" | grep -v "^\.knowledge/\.logs" | grep -v "^\.knowledge/\.pending" | grep -v "^\.knowledge/\.sources" | grep -v "^\.knowledge/README" | grep -v "^\.knowledge/CLAUDE" | grep -v "^\.knowledge/AGENTS" || true)
NEW_DOC_COUNT=$(echo "$NEW_DOCS" | grep -c "." 2>/dev/null || echo "0")

# 检查索引年龄
META_FILE="$KB_DIR/.index/_meta.yaml"
NEEDS_REBUILD=false
if [ -f "$META_FILE" ]; then
  LAST_REBUILD=$(grep "last_full_rebuild" "$META_FILE" | head -1 | awk '{print $2}' | tr -d '"')
  if [ -n "$LAST_REBUILD" ]; then
    REBUILD_EPOCH=$(date -j -f "%Y-%m-%d" "$LAST_REBUILD" "+%s" 2>/dev/null || date -d "$LAST_REBUILD" "+%s" 2>/dev/null || echo "0")
    NOW_EPOCH=$(date "+%s")
    DAYS_SINCE=$(( (NOW_EPOCH - REBUILD_EPOCH) / 86400 ))
    if [ "$DAYS_SINCE" -gt 30 ]; then
      NEEDS_REBUILD=true
    fi
  fi
fi

# ─── 输出提示 ───
echo ""
echo "📚 [post-merge] 知识库变更检测"
echo "   本次合并涉及 $CHANGED_COUNT 个知识库文件（其中 $NEW_DOC_COUNT 个业务文档）"

if [ "$NEW_DOC_COUNT" -gt 3 ]; then
  echo ""
  echo "   💡 建议运行索引重建以保证一致性："
  echo "      /knowledge-wiki health index-rebuild"
fi

if [ "$NEEDS_REBUILD" = true ]; then
  echo ""
  echo "   ⚠️  索引上次重建距今 ${DAYS_SINCE} 天（超过 30 天阈值）"
  echo "      强烈建议运行：/knowledge-wiki health index-rebuild"
fi

# 检查是否有 pending backlinks 文件被修改
if echo "$CHANGED_KB_FILES" | grep -q "pending-backlinks"; then
  echo ""
  echo "   🔗 .pending-backlinks.yaml 有更新，建议运行："
  echo "      /knowledge-wiki health backlink-consume"
fi

echo ""
exit 0