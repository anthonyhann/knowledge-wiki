#!/bin/bash
# knowledge-wiki pre-push hook
# 阻断式确认：检测即将过期/已过期文档 + 陈旧外部源
# 无问题时完全静默，不干扰正常 push 流程
KNOWLEDGE_DIR=".knowledge"
[ ! -d "$KNOWLEDGE_DIR" ] && exit 0

CHANGED=$(git diff --name-only @{u} HEAD 2>/dev/null || git diff --name-only HEAD~1 HEAD 2>/dev/null)
[ -z "$CHANGED" ] && exit 0

# 检查 expires ≤7 天或已过期的文档
EXPIRING=$(find "$KNOWLEDGE_DIR" -name "*.md" | xargs grep -l "^expires:" 2>/dev/null | while read f; do
  exp=$(grep "^expires:" "$f" | awk '{print $2}')
  [ "$exp" = "never" ] && continue
  days=$(( ($(date -d "$exp" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$exp" +%s) - $(date +%s)) / 86400 ))
  [ "$days" -le 7 ] && echo "$f（$days 天后过期）"
done)

# 检查陈旧外部源（last_synced > 30 天）
STALE=""
if [ -f "$KNOWLEDGE_DIR/.sources.yaml" ]; then
  STALE=$(python3 -c "
import yaml
from datetime import datetime
with open('$KNOWLEDGE_DIR/.sources.yaml') as f:
    data = yaml.safe_load(f) or {}
for s in data.get('sources', []):
    ls = s.get('last_synced', '')
    if ls and (datetime.now() - datetime.strptime(ls, '%Y-%m-%d')).days > 30:
        print(s['id'] + '（' + ls + '）')
" 2>/dev/null)
fi

[ -z "$EXPIRING" ] && [ -z "$STALE" ] && exit 0  # 无问题，静默放行

echo ""
echo "⚠️  知识库同步检查（pre-push）"
echo "─────────────────────────────────────"
[ -n "$EXPIRING" ] && echo "[文档即将过期]" && echo "$EXPIRING"
[ -n "$STALE" ]    && echo "[外部源可能陈旧]" && echo "$STALE"
echo ""
echo "请选择："
echo "  [1] 现在处理（在 Claude 中运行 /knowledge-wiki health 后重新 push）"
echo "  [2] 跳过（直接 push）"
echo "  [3] 中止 push"
read -p "输入选项 [1/2/3]: " choice
case "$choice" in
  1) echo "请处理后重新 push"; exit 1 ;;
  3) echo "已中止"; exit 1 ;;
  *) exit 0 ;;
esac

