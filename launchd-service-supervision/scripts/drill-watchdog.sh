#!/usr/bin/env bash
# 「杀-等-起」演练：验证守护真的能把死掉的服务拉回来。
# 用法: drill-watchdog.sh <launchd-label> <pkill命令行特征> <健康检查URL>
# 例:   drill-watchdog.sh com.foo.watchdog "Foo/apps/api/src/main.ts" http://127.0.0.1:3001/api/health
set -uo pipefail

LABEL="${1:?用法: drill-watchdog.sh <label> <pkill特征> <健康URL>}"
PATTERN="${2:?缺少 pkill 特征}"
URL="${3:?缺少健康检查 URL}"

probe() { curl -s -o /dev/null -w "%{http_code}" -m 6 "$URL"; }

before="$(probe)"
echo "演练前 $URL → $before"
[ "$before" = "200" ] || echo "⚠️  演练前就没起来，先让服务正常再演练"

echo "杀掉：pkill -f \"$PATTERN\""
pkill -f "$PATTERN"
sleep 3
echo "杀掉后 → $(probe)（应为 000）"

echo "触发守护：launchctl kickstart -k gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL" || { echo "❌ kickstart 失败：label 没登记？"; exit 1; }

for i in $(seq 1 12); do
  sleep 5
  code="$(probe)"
  echo "  等待 $((i*5))s → $code"
  [ "$code" = "200" ] && { echo "✅ 已恢复（守护生效）"; exit 0; }
done
echo "❌ 60 秒内未恢复：看 .logs/watchdog.log 与 .logs/*.log"
exit 1
