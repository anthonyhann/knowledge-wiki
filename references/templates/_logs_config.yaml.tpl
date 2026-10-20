# .knowledge/.logs/_config.yaml
# 由 /knowledge-wiki init 自动生成，后续按需调整
# 详见 references/log-rules.md

version: 1

# 归档规则
archive:
  max_entries_per_file: 150       # 单文件超过此条数时触发归档
  max_days: 90                    # 或超过此天数也触发（先到为准）
  format: "{owner}-{YYYY-Q}.md"   # 归档文件名格式（按季度）

# 脱敏规则
sensitive_actions:
  ask:
    mode: hash                    # ask 内容只记 sha1(内容) 前 8 位
    # 例：ask: "a1b2c3d4" 而非 ask: "配送超时怎么配置"
  ingest:
    mode: plain                   # 录入操作记录 title 明文（需要，用于追溯）

# digest 聚合规则
digest:
  auto_generate_on: health        # 每次 health（无子命令）执行时自动重新生成
  keep_recent: 50                 # digest 只保留最近 50 条
  include_personal_files: true    # 聚合所有 personal/*.md
  sort_by: time_desc              # 按时间倒序

# 覆盖率缺口分析（依赖 log 数据）
gap_analysis:
  min_window_days: 7              # 至少积累 7 天数据才分析
  min_hit_count: 3                # 同类去重后 ≥3 次未命中才算缺口
  anonymize: true                 # 聚合时去掉 @who 信息