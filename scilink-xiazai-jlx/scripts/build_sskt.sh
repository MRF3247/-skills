#!/bin/bash
# 全书重建：md → 正文 PDF → 目录 PDF → 合并 → 加链接 → 截图 → 打包
set -e
cd "/Users/Jin/Documents/Open Programs/funasr"
PY="/Users/Jin/Documents/Open Programs/funasr/.venv/bin/python"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

echo "[1/7] 合并 md"
"$PY" combine_sskt.py

echo "[2/7] 正文 HTML"
cd sskt_book/book
MD2PDF="/Users/Jin/Documents/Open Programs/funasr/md2pdf.py"
"$PY" "$MD2PDF" 全书.md ./_body.html >/dev/null

echo "[3/7] 正文 PDF"
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="/tmp/sskt_body.pdf" \
  "file:///Users/Jin/Documents/Open Programs/funasr/sskt_book/book/_body.html" 2>/dev/null

echo "[4/7] 目录"
cd "/Users/Jin/Documents/Open Programs/funasr"
"$PY" make_toc_sskt4.py
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="/tmp/sskt_toc.pdf" \
  "file:///Users/Jin/Documents/Open Programs/funasr/sskt_book/book/_toc.html" 2>/dev/null

echo "[5/7] 合并成书"
"$PY" merge_sskt.py

echo "[6/7] 加书签和跳转"
"$PY" add_toc_links.py

echo "[7/7] 导出截图"
"$PY" export_sskt_toc.py

echo "完成"
