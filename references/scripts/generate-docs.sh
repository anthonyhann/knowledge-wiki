#!/usr/bin/env bash
# generate-docs.sh — 生成 docs/generated/ 下的自动产物
# 触发时机：pre-push hook 自动调用，或手动运行
# 用法：bash processes/scripts/generate-docs.sh [--all|--schema|--changelog]

set -euo pipefail

KB_DIR=".knowledge"
GENERATED_DIR="${KB_DIR}/docs/generated"
mkdir -p "$GENERATED_DIR"

MODE="${1:---all}"

# ── db-schema.md：从 SQL migration 文件提取表结构摘要 ────────────────
generate_schema() {
  SCHEMA_OUT="${GENERATED_DIR}/db-schema.md"
  # 查找项目中的 migration 文件（支持 Go/PHP 常见路径）
  MIGRATION_DIRS=("db/migrations" "database/migrations" "internal/db" "migrations")
  SQL_FILES=()
  for dir in "${MIGRATION_DIRS[@]}"; do
    [ -d "$dir" ] && SQL_FILES+=("$dir"/*.sql) 2>/dev/null || true
  done

  if [ ${#SQL_FILES[@]} -eq 0 ]; then
    echo "  [skip] 未找到 migration 文件，跳过 db-schema.md 生成"
    return
  fi

  {
    echo "---"
    echo "generated: $(date +%Y-%m-%d)"
    echo "status: auto"
    echo "---"
    echo "<!-- 由 generate-docs.sh 自动生成，禁止手动编辑 -->"
    echo ""
    echo "# 数据库结构摘要"
    echo ""
    echo "> 来源：${SQL_FILES[*]}"
    echo ""
    # 提取 CREATE TABLE 语句
    grep -h "CREATE TABLE\|--" "${SQL_FILES[@]}" 2>/dev/null | head -200 || true
  } > "$SCHEMA_OUT"
  echo "  ✓ db-schema.md 已更新"
}

# ── api-changelog.md：从 git diff 提取接口文件变更摘要 ───────────────
generate_api_changelog() {
  CHANGELOG_OUT="${GENERATED_DIR}/api-changelog.md"
  # 找最近一个 tag 作为基准，无 tag 则用 HEAD~10
  BASE=$(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~10")
  API_PATTERNS=("*.proto" "*_api.go" "*handler*.go" "*controller*.php" "*Controller*.go")

  CHANGED_API_FILES=""
  for pat in "${API_PATTERNS[@]}"; do
    files=$(git diff --name-only "$BASE" HEAD -- "$pat" 2>/dev/null || true)
    CHANGED_API_FILES="${CHANGED_API_FILES}${files}"
  done

  {
    echo "---"
    echo "generated: $(date +%Y-%m-%d)"
    echo "status: auto"
    echo "---"
    echo "<!-- 由 generate-docs.sh 自动生成，禁止手动编辑 -->"
    echo ""
    echo "# 接口变更日志"
    echo ""
    echo "> 对比基准：\`${BASE}\`  生成时间：$(date +%Y-%m-%d)"
    echo ""
    if [ -z "$CHANGED_API_FILES" ]; then
      echo "自 \`${BASE}\` 以来无接口文件变更。"
    else
      echo "## 变更文件"
      echo "\`\`\`"
      echo "$CHANGED_API_FILES"
      echo "\`\`\`"
      echo ""
      echo "## 变更摘要"
      git diff "$BASE" HEAD -- ${API_PATTERNS[@]} 2>/dev/null \
        | grep "^[+-]" | grep -v "^---\|^+++" | head -100 || true
    fi
  } > "$CHANGELOG_OUT"
  echo "  ✓ api-changelog.md 已更新"
}

case "$MODE" in
  --schema)    generate_schema ;;
  --changelog) generate_api_changelog ;;
  --all|*)
    generate_schema
    generate_api_changelog
    ;;
esac
