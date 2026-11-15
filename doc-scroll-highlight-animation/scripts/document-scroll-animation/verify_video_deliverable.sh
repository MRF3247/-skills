#!/usr/bin/env bash
# 用法: verify_video_deliverable.sh <视频文件> [降采样宽度，默认160]
# 用途：独立复核成片/渲染产物 —— 大小·sha256·时长·分辨率·fps·音轨·帧唯一性
# 帧唯一性：完全重复帧 = 静止段，用户会数出来并打回，必须为 0
set -u
F="${1:?用法: verify_video_deliverable.sh <视频文件> [降采样宽度]}"
W="${2:-160}"
[ -f "$F" ] || { echo "文件不存在: $F"; exit 1; }

echo "=== $F"
ls -la "$F" | awk '{print "  大小: "$5" bytes   修改: "$6" "$7" "$8}'
shasum -a 256 "$F" | awk '{print "  sha256: "substr($1,1,32)"…（台账登记前16位即可）"}'

echo "--- 流信息（本机 ffprobe 残缺失效，用 ffmpeg -i 探） ---"
ffmpeg -i "$F" 2>&1 | grep -E "Duration|Stream" | sed 's/^/  /'
if ffmpeg -i "$F" 2>&1 | grep -q "Stream.*Audio"; then
  echo "  ⚠ 含音轨——若交付要求静音（防外放）需确认是否预期"
else
  echo "  ✓ 无音轨（静音合规）"
fi

echo "--- 帧唯一性 ---"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if ! ffmpeg -v error -i "$F" -vf "scale=${W}:-1" -vsync 0 -f image2 "$TMP/f%05d.png"; then
  echo "  ✗ 抽帧失败，无法判定"; exit 1
fi
TOTAL=$(ls "$TMP" | wc -l | tr -d ' ')
DUP=$(md5 -q "$TMP"/*.png 2>/dev/null | sort | uniq -d | wc -l | tr -d ' ')
echo "  帧总数=$TOTAL  完全重复帧数=$DUP"
if [ "$DUP" -eq 0 ]; then echo "  ✓ 无完全重复帧"; else echo "  ⚠ 存在重复帧：静止段过长或编码异常，修渲染后重跑（给停驻段加极缓运动）"; fi
