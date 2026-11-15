#!/usr/bin/env bash
# 小红书海报渲染：把多页 HTML 拆成单页，逐页 Chrome headless 截图。
# 用法：scripts/render_posters.sh <输入.html> [输出目录]
#   - 输入 HTML 用 <!-- ==== N 标题 ==== --> 注释分页
#   - 可选 <输入文件名>.页名.txt（每行一个页名）控制输出文件名；缺省自动 01、02…
# 输出：<输出目录>/NN_页名.png（1242×1656 @2x，等效 2484×3312）
set -euo pipefail

INPUT="${1:-海报模板.html}"
OUT_DIR="${2:-渲染输出}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TMP="_single_$$"
mkdir -p "$OUT_DIR" "$TMP"

python3 - "$INPUT" "$TMP" << 'PYEOF'
import re, os, sys
html_path, tmp = sys.argv[1], sys.argv[2]
html = open(html_path, encoding="utf-8").read()
style = re.search(r"<style>.*?</style>", html, re.S).group(0)
segments = re.split(r"<!-- =+ \d+ [^=]+ =+ -->", html)
pages = [s.strip() for s in segments if 'class="page' in s]
names_file = os.path.splitext(html_path)[0] + ".页名.txt"
names = [l.strip() for l in open(names_file, encoding="utf-8") if l.strip()] \
    if os.path.exists(names_file) else [f"{i+1:02d}" for i in range(len(pages))]
for i, (name, part) in enumerate(zip(names, pages), 1):
    single = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8">{style}</head>
<body>{part}</body></html>"""
    open(os.path.join(tmp, f"{i:02d}_{name}.html"), "w", encoding="utf-8").write(single)
print(f"拆分 {len(pages)} 页")
PYEOF

for f in "$TMP"/*.html; do
  base="$(basename "$f" .html)"
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=2 \
    --window-size=1242,1656 \
    --screenshot="$OUT_DIR/$base.png" \
    "file://$(cd "$(dirname "$f")" && pwd)/$(basename "$f")" 2>/dev/null
  echo "渲染: $base"
done
rm -rf "$TMP"
echo "完成 → $OUT_DIR"
