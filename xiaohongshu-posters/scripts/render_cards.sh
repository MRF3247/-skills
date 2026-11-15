#!/bin/bash
# 文字卡渲染：逐页 Chrome headless 截图（2x 像素密度）+ 回读自动适配结果
# 用法：render_cards.sh <pages目录> [输出目录] [宽] [高]
# 前提：pages 里是每页一个独立 HTML（多页 HTML 无法滚动截取，必须先拆页）
set -u
PAGES="${1:?用法: render_cards.sh <pages目录> [输出目录]}"
OUTDIR="${2:-$(dirname "$PAGES")/png}"
W="${3:-1242}"; H="${4:-1656}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
mkdir -p "$OUTDIR"
cd "$PAGES" || exit 1

for f in *.html; do
  n="${f%.html}"
  "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=2 --default-background-color=00000000 \
    --virtual-time-budget=6000 \
    --window-size=$W,$H \
    --screenshot="$OUTDIR/$n.png" \
    "file://$PAGES/$f" >/dev/null 2>&1
  echo "  渲染 $n.png  $( [ -f "$OUTDIR/$n.png" ] && echo OK || echo 失败 )"
done

# 回读每页适配结果：fill 接近 100% 说明该卡已顶到可用高度上限
# --virtual-time-budget 必须给足，否则 JS 未跑完就导出，拿到的是默认字号
echo "--- 自动适配结果（fill = 可用高度占用率，100% 为顶格） ---"
for f in *.html; do
  n="${f%.html}"
  "$CHROME" --headless=new --disable-gpu --no-sandbox --virtual-time-budget=6000 \
      --dump-dom "file://$PAGES/$f" 2>/dev/null \
    | grep -o '<title>[^<]*</title>' | head -1 \
    | sed "s|<title>|  $n  |; s|</title>||"
done
echo "输出目录: $OUTDIR"
