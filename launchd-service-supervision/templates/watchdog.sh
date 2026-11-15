#!/usr/bin/env bash
# 服务守护模板：拷到项目根目录，改下面 CHECKS / START 两组变量即可。
# 配套 watchdog.plist 用 StartInterval 300 + AbandonProcessGroup=true。
# 手动暂停：touch .logs/paused（恢复：rm .logs/paused）
set -uo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"      # 项目根（路径不能有空格）
START="$ROOT/start.sh"                     # ← 改成项目的启动脚本（必须幂等、只补缺的）
CHECKS=(                                    # ← 改成要探活的地址；任一失败就重启
  "http://127.0.0.1:3001/api/health"
  "http://127.0.0.1:3000/"
)

STATE="$ROOT/.logs"
LOG="$STATE/watchdog.log"
mkdir -p "$STATE"
log() { echo "[$(date '+%F %T')] $*" >>"$LOG"; }

[ -f "$STATE/paused" ] && exit 0

failed=""
for url in "${CHECKS[@]}"; do
  curl -s -o /dev/null -m 6 "$url" || failed="$failed $url"
done
[ -z "$failed" ] && exit 0

log "服务异常（失败：$failed）→ 执行 $START"
( cd "$ROOT" && "$START" ) >>"$LOG" 2>&1
sleep 12

for url in "${CHECKS[@]}"; do
  curl -s -o /dev/null -m 6 "$url" || { log "仍未恢复：$url"; exit 1; }
done
log "已恢复"
