"""
Markdown → 教材版式 HTML（供 Chrome 打印成 PDF）
"""
import re
import sys

import markdown

SRC = sys.argv[1]
OUT = sys.argv[2]

md = open(SRC, encoding="utf-8").read()
html_body = markdown.markdown(
    md, extensions=["tables", "fenced_code", "sane_lists", "nl2br"]
)

CSS = """
@page { size: A4; margin: 20mm 18mm 18mm 18mm; }
* { box-sizing: border-box; }
body {
  font-family: "Songti SC", "STSong", "SimSun", serif;
  font-size: 11.5pt; line-height: 1.95; color: #1c1c1c;
  text-align: justify; hyphens: none;
}
h1, h2, h3, h4 {
  font-family: "PingFang SC", "Hiragino Sans GB", "Heiti SC", sans-serif;
  color: #12202e; break-after: avoid; page-break-after: avoid;
}
h1 {
  font-size: 20pt; margin: 0 0 6pt; padding-bottom: 8pt;
  border-bottom: 2.5pt solid #12202e; letter-spacing: .5pt;
}
h2 {
  font-size: 15pt; margin: 22pt 0 9pt; padding-left: 9pt;
  border-left: 4pt solid #2f5f8f;
}
h3 { font-size: 12.5pt; margin: 15pt 0 6pt; color: #1f3a55; }
p { margin: 0 0 8.5pt; }
strong { font-weight: 700; color: #0d1620; }
em { font-style: normal; color: #4a5560; }

/* 图片 */
img { max-width: 100%; display: block; margin: 10pt auto 4pt; }
p > img + em, p em:only-child {
  display: block; text-align: center; font-size: 9.5pt; color: #6b7885;
  margin-top: 4pt; font-family: "PingFang SC", sans-serif;
}

/* 引用块（大白话 / 比喻 / 讲师原话） */
blockquote {
  margin: 9pt 0; padding: 9pt 12pt; background: #f7f8fa;
  border-left: 3pt solid #b8c4d0; color: #33414f; font-size: 10.8pt;
}
blockquote p { margin: 0 0 5pt; }
blockquote p:last-child { margin-bottom: 0; }

/* 表格 */
table {
  width: 100%; border-collapse: collapse; margin: 10pt 0 12pt;
  font-size: 10pt; font-family: "PingFang SC", sans-serif;
  break-inside: avoid; page-break-inside: avoid;
}
th, td { border: 0.6pt solid #d5dbe2; padding: 5pt 7pt; text-align: left; vertical-align: top; line-height: 1.6; }
th { background: #eef2f6; font-weight: 700; color: #12202e; }
td:first-child { white-space: nowrap; }

/* 列表 */
ul, ol { margin: 0 0 9pt; padding-left: 17pt; }
li { margin-bottom: 4pt; }
li > p { margin-bottom: 3pt; }

/* 代码 */
code {
  font-family: "SF Mono", Menlo, monospace; font-size: 9.5pt;
  background: #f0f3f6; padding: 1pt 3.5pt; border-radius: 2pt; color: #1f3a55;
}

/* 分隔线 */
hr { border: none; border-top: 0.8pt solid #dfe4ea; margin: 16pt 0; }

/* 本篇小结等特殊段 */
h2 + table { margin-top: 8pt; }

/* 避免表格/图片被劈开 */
h1, h2, h3 { break-inside: avoid; }
"""

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>医学文献检索与阅读 · 第一篇</title>
<style>{CSS}</style></head>
<body>{html_body}</body></html>"""

open(OUT, "w", encoding="utf-8").write(HTML)
print(f"HTML 已写：{OUT}")
