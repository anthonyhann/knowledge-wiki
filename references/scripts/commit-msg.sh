#!/bin/bash
# knowledge-wiki commit-msg hook
# [kb] 标记触发，不阻断 commit，仅输出建议
COMMIT_MSG=$(cat "$1")
echo "$COMMIT_MSG" | grep -q "\[kb\]" || exit 0

KNOWLEDGE_DIR=".knowledge"
CLEAN_MSG=$(echo "$COMMIT_MSG" | sed 's/\[kb\]//g' | xargs)

echo ""
echo "📝 [kb] 检测到知识录入标记"
echo "─────────────────────────────────────"
echo "commit：$CLEAN_MSG"
RELATED=$(rg --files-with-matches "$CLEAN_MSG" "$KNOWLEDGE_DIR" 2>/dev/null | head -3)
if [ -n "$RELATED" ]; then
  echo "相关现有文档："; echo "$RELATED"
  echo "建议：/knowledge-wiki in --update <slug> 或 /knowledge-wiki in <描述>"
else
  echo "知识库暂无相关文档，建议：/knowledge-wiki in $CLEAN_MSG"
fi
echo "─────────────────────────────────────"
exit 0

